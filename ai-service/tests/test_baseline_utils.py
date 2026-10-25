import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from baseline_utils import metrics_from_predictions

class MetricsTests(unittest.TestCase):
    def test_perfect(self):
        x=metrics_from_predictions([0,1,1,0],[0,1,1,0])
        self.assertEqual(x['confusion_matrix'],[[2,0],[0,2]])
        self.assertAlmostEqual(x['macro_f1'],1.)
    def test_errors(self):
        x=metrics_from_predictions([0,0,1,1],[0,1,0,1])
        self.assertEqual(x['confusion_matrix'],[[1,1],[1,1]])
        self.assertAlmostEqual(x['by_class']['occupied']['f1'],.5)

if __name__=='__main__':unittest.main()
