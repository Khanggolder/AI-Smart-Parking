"""Evaluate a frozen baseline checkpoint. Test split must be used only once after selection."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import torch
from torch.utils.data import DataLoader

ROOT=Path(__file__).resolve().parents[1]
REPO_ROOT=ROOT.parent
sys.path.insert(0,str(ROOT/'src'))
from dataset import ParkingSpotDataset
from baseline_utils import (assert_safe_splits, create_model, dump_json,
                            metrics_from_predictions, predict_all,
                            save_confusion_png, select_device)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkpoint',default='ai-service/runs/mobilenetv3_baseline/best.pt')
    p.add_argument('--split',choices=('val','test'),default='val')
    p.add_argument('--batch-size',type=int,default=32)
    p.add_argument('--device',choices=('auto','cpu','cuda'),default='auto')
    p.add_argument('--output',default='ai-service/runs/mobilenetv3_baseline/evaluation')
    args=p.parse_args()
    split_stats=assert_safe_splits(ROOT/'manifests')
    ckpt_path=REPO_ROOT/args.checkpoint
    checkpoint=torch.load(ckpt_path,map_location='cpu',weights_only=True)
    if checkpoint.get('architecture')!='mobilenet_v3_small' or checkpoint.get('class_names')!=['empty','occupied']:
        raise ValueError('Unexpected checkpoint architecture/label order')
    saved=checkpoint.get('split_stats')
    if saved and any(saved[s]['sha256']!=split_stats[s]['sha256'] for s in split_stats):
        raise RuntimeError('Manifest checksum changed since training; do not evaluate on a different split.')
    if args.split=='test':
        print('[NOTICE] Evaluating held-out TEST set. Do not use test metrics to select or retune the model.')
    device=select_device(args.device)
    model=create_model(pretrained=False)
    model.load_state_dict(checkpoint['model_state'],strict=True)
    model=model.to(device)
    ds=ParkingSpotDataset(ROOT/'manifests'/f'{args.split}.csv',REPO_ROOT,train=False)
    loader=DataLoader(ds,batch_size=args.batch_size,shuffle=False,num_workers=0)
    truth,preds,_=predict_all(model,loader,device)
    result=metrics_from_predictions(truth,preds)
    result['split']=args.split
    result['checkpoint']=str(ckpt_path)
    result['selected_epoch']=checkpoint.get('selected_epoch')
    result['manifest_sha256']=split_stats[args.split]['sha256']
    out=REPO_ROOT/args.output
    dump_json(out/f'{args.split}_metrics.json',result)
    save_confusion_png(result['confusion_matrix'],out/f'{args.split}_confusion_matrix.png',f'{args.split.capitalize()} confusion matrix')
    print(f"{args.split.upper()}: accuracy={result['accuracy']:.4f} macro_f1={result['macro_f1']:.4f}")
    for name,score in result['by_class'].items():
        print(f" {name:8} precision={score['precision']:.4f} recall={score['recall']:.4f} f1={score['f1']:.4f} support={score['support']}")
    print(f"Confusion matrix [true rows x predicted columns]: {result['confusion_matrix']}")
    print(f'[PASS] Results: {out}')

if __name__=='__main__':
    main()
