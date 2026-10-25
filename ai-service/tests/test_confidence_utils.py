from pathlib import Path
import hashlib
import importlib.util
import subprocess
import sys
import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from confidence_utils import decide, selective_summary, expected_calibration_error
from dataset import LABEL_TO_ID, ParkingSpotDataset


def test_unknown_below_threshold():
    d = decide(.46, .54, .9)
    assert d['label'] == 'unknown'
    assert d['raw_label'] == 'occupied'
    assert d['confidence'] == .54


def test_class_decisions():
    assert decide(.91, .09, .9)['label'] == 'empty'
    assert decide(.01, .99, .9)['label'] == 'occupied'
    assert decide(.1, .9, .9)['label'] == 'occupied'  # inclusive threshold


def test_invalid_probabilities_rejected():
    for a, b in ((.9, .9), (float('nan'), .2), (float('inf'), 0),
                 (-.1, 1.1), (.7, .2)):
        with pytest.raises(ValueError):
            decide(a, b, .9)
    for threshold in (.4, 1.1, float('nan'), float('inf')):
        with pytest.raises(ValueError):
            decide(.5, .5, threshold)


def test_selective_confusion_and_coverage():
    truth = [0, 1, 0, 1]
    p = np.asarray([[.91, .09], [.08, .92], [.55, .45], [.65, .35]])
    s = selective_summary(truth, p, .9)
    assert s['accepted'] == 2 and s['unknown'] == 2
    assert s['coverage'] == .5
    assert s['accepted_accuracy'] == 1.0
    assert s['confusion_matrix_true_rows_predicted_cols_empty_occupied_unknown'] == [[1, 0, 1], [0, 1, 1]]


def test_ece_perfect_one_hot():
    assert expected_calibration_error([0, 1], np.asarray([[1.,0.],[0.,1.]])) == 0.


def test_class_mapping_and_boundary():
    assert LABEL_TO_ID == {'empty': 0, 'occupied': 1}
    assert decide(.5, .5, .5)['label'] == 'empty'  # deterministic tie break
    assert decide(.99, .01, .99)['label'] == 'empty'
    assert decide(.99, .01, 1.0)['label'] == 'unknown'


def test_summary_rejects_invalid_inputs_without_mutation():
    original = np.asarray([[.91, .09], [.1, .9]])
    snapshot = original.copy()
    assert selective_summary([0, 1], original, .9)['accepted'] == 2
    np.testing.assert_array_equal(original, snapshot)
    for values in (np.asarray([[float('nan'), .5]]),
                   np.asarray([[float('inf'), 0.]]),
                   np.asarray([[.6, .6]])):
        with pytest.raises(ValueError):
            selective_summary([0], values, .9)
    with pytest.raises(ValueError):
        selective_summary([0, 1], original, float('nan'))


def test_no_accepted_predictions():
    result = selective_summary([0, 1], np.asarray([[.51, .49], [.49, .51]]), .9)
    assert result['accepted'] == 0
    assert result['unknown'] == 2
    assert result['accepted_accuracy'] is None
    assert result['unknown_by_true_class'] == {'empty': 1, 'occupied': 1}


def test_synthetic_variants_do_not_modify_source_crop(tmp_path):
    crop = tmp_path / 'crop.png'
    Image.new('RGB', (224, 224), (100, 150, 200)).save(crop)
    manifest = tmp_path / 'val.csv'
    manifest.write_text('crop_path,label\ncrop.png,occupied\n', encoding='utf-8')
    before = hashlib.sha256(crop.read_bytes()).hexdigest()
    base = ParkingSpotDataset(manifest, tmp_path)
    script = Path(__file__).resolve().parents[1] / 'scripts' / 'analyze_confidence.py'
    spec = importlib.util.spec_from_file_location('analyze_confidence', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for variant in ('brightness_0.6', 'contrast_0.5', 'center_occlusion_35pct'):
        tensor, label = module.SyntheticValidationDataset(base, variant)[0]
        assert tensor.shape == (3, 224, 224)
        assert label == 1
    assert hashlib.sha256(crop.read_bytes()).hexdigest() == before


def test_confidence_cli_does_not_offer_test_split():
    script = Path(__file__).resolve().parents[1] / 'scripts' / 'analyze_confidence.py'
    result = subprocess.run([sys.executable, str(script), '--split', 'test'],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 2
    assert 'unrecognized arguments: --split test' in result.stderr
