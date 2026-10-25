"""MobileNetV3-Small transfer-learning baseline for AI Smart Parking W2.

Launch from repo root:
 python ai-service/scripts/train_baseline.py --weights pretrained --epochs 8
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import sys
from datetime import datetime, timezone

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader

SERVICE_ROOT=Path(__file__).resolve().parents[1]
REPO_ROOT=SERVICE_ROOT.parent
sys.path.insert(0, str(SERVICE_ROOT/'src'))
from dataset import ParkingSpotDataset
from baseline_utils import (assert_safe_splits, create_model, dump_json,
                            metrics_from_predictions, predict_all,
                            save_confusion_png, select_device)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--weights', choices=('pretrained','none'), default='pretrained')
    parser.add_argument('--epochs', type=int, default=8)
    parser.add_argument('--batch-size', type=int, default=32)
    parser.add_argument('--device', choices=('auto','cpu','cuda'), default='auto')
    parser.add_argument('--num-workers', type=int, default=0)
    parser.add_argument('--lr-head', type=float, default=0.001)
    parser.add_argument('--lr-backbone', type=float, default=0.00002)
    parser.add_argument('--unfreeze-at', type=int, default=3, help='1-indexed epoch, 0 = never unfreeze')
    parser.add_argument('--patience', type=int, default=4)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--max-batches', type=int, default=0, help='Only for smoke tests, 0 = all batches')
    parser.add_argument('--output', default='ai-service/runs/mobilenetv3_baseline')
    args=parser.parse_args()
    if args.epochs < 1 or args.batch_size < 1 or args.patience < 1 or args.num_workers < 0:
        parser.error('epochs, batch-size, patience must be positive and num-workers nonnegative')
    if args.weights=='none':
        print('[WARNING] Randomly initialized backbone. Use this only for pipeline smoke tests, not a real transfer-learning baseline.')

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(args.seed)

    split_stats=assert_safe_splits(SERVICE_ROOT/'manifests')
    for split, info in split_stats.items():
        print(f"{split}: {info['rows']} crops, {info['days']} days, {info['labels']}")
        if set(info['labels']) != {'empty','occupied'}:
            raise RuntimeError(f'{split} missing an occupancy class; resolve the dataset split first')
    device=select_device(args.device)
    print(f'Device: {device}, Torch: {torch.__version__}')
    ds_train=ParkingSpotDataset(SERVICE_ROOT/'manifests/train.csv', REPO_ROOT, train=True)
    ds_val=ParkingSpotDataset(SERVICE_ROOT/'manifests/val.csv', REPO_ROOT, train=False)
    train_loader=DataLoader(ds_train,batch_size=args.batch_size,shuffle=True,
                            num_workers=args.num_workers,pin_memory=device.type=='cuda')
    val_loader=DataLoader(ds_val,batch_size=args.batch_size,shuffle=False,
                          num_workers=args.num_workers,pin_memory=device.type=='cuda')

    pretrained=args.weights=='pretrained'
    model=create_model(pretrained=pretrained,freeze_features=pretrained).to(device)
    optimizer=torch.optim.AdamW([
        {'params':list(model.features.parameters()),'lr':args.lr_backbone},
        {'params':list(model.classifier.parameters()),'lr':args.lr_head},
    ],weight_decay=1e-4)
    criterion=nn.CrossEntropyLoss()
    output=REPO_ROOT/args.output
    output.mkdir(parents=True,exist_ok=True)
    history=[]
    best_f1=-1.0
    stale=0
    unfrozen=not pretrained
    for epoch in range(1,args.epochs+1):
        if pretrained and not unfrozen and args.unfreeze_at > 0 and epoch>=args.unfreeze_at:
            for p in model.features.parameters(): p.requires_grad=True
            unfrozen=True
            print(f'[INFO] Fine-tuning entire network from epoch {epoch}')
        model.train()
        if not unfrozen:
            model.features.eval()  # Keep pretrained backbone BatchNorm statistics unchanged while frozen.
        train_loss=0.0
        n=0
        for idx,(xb,yb) in enumerate(train_loader):
            if args.max_batches and idx>=args.max_batches:break
            xb,yb=xb.to(device),yb.to(device)
            optimizer.zero_grad(set_to_none=True)
            logits=model(xb)
            loss=criterion(logits,yb)
            loss.backward()
            optimizer.step()
            train_loss+=float(loss.item())*len(yb)
            n+=len(yb)
        truth,preds,val_loss=predict_all(model,val_loader,device,criterion)
        val=metrics_from_predictions(truth,preds)
        row={'epoch':epoch,'train_loss':train_loss/max(n,1),'val_loss':val_loss,
             'val_accuracy':val['accuracy'],'val_macro_f1':val['macro_f1'],
             'val_occupied_f1':val['by_class']['occupied']['f1']}
        history.append(row)
        print(f"Epoch {epoch:02d}/{args.epochs} | train_loss={row['train_loss']:.4f} | "
              f"val_loss={row['val_loss']:.4f} | val_macro_f1={row['val_macro_f1']:.4f} | "
              f"val_occupied_f1={row['val_occupied_f1']:.4f}",flush=True)
        if val['macro_f1']>best_f1+1e-6:
            best_f1=val['macro_f1']
            stale=0
            checkpoint={'model_state':model.state_dict(), 'architecture':'mobilenet_v3_small',
                        'num_classes':2,'class_names':['empty','occupied'],
                        'image_size':224,'weights_source':args.weights,
                        'preprocess':'W1 ParkingSpotDataset ImageNet normalize',
                        'val_macro_f1':best_f1, 'selected_epoch':epoch,
                        'split_stats':split_stats, 'seed':args.seed,
                        'created_utc':datetime.now(timezone.utc).isoformat()}
            torch.save(checkpoint,output/'best.pt')
            dump_json(output/'best_val_metrics.json',val)
            save_confusion_png(val['confusion_matrix'],output/'val_confusion_matrix.png','Best validation confusion matrix')
        else:
            stale+=1
        dump_json(output/'history.json',{'epochs':history,'args':vars(args)})
        if stale>=args.patience:
            print(f'Early stopping: no validation macro-F1 improvement for {stale} epochs.')
            break
    print(f'[PASS] Checkpoint saved: {output / "best.pt"}')
    print('Next: run evaluate_baseline.py --split test only AFTER final model selection.')
    if args.max_batches:
        print('[WARNING] --max-batches was used: this is only a smoke test, NOT a valid trained baseline.')

if __name__=='__main__':
    main()
