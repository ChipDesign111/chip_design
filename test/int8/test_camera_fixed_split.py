"""Fixed original clip splits after train/validation cleaning; synthetic rows only."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from fpga.demo.features import DEFAULT_LABELS
from fpga.demo.train_camera import _class_accuracies, _split_details, split_sessions


def fixture():
    labels, sessions, mapping = [], [], {}
    for label in DEFAULT_LABELS:
        for split in ('train', 'validation', 'test'):
            session = label + '-' + split
            mapping[session] = split
            labels.extend([label] * 2)
            sessions.extend([session] * 2)
    return np.array(labels), np.array(sessions), mapping


class FixedSessionSplitTests(unittest.TestCase):
    def test_default_seeded_split_still_requires_three_independent_sessions(self):
        labels, sessions, _ = fixture()
        indices, first = split_sessions(labels, sessions, DEFAULT_LABELS, seed=42)
        second_indices, second = split_sessions(labels, sessions, DEFAULT_LABELS, seed=42)
        self.assertEqual(first, second)
        for split in indices:
            np.testing.assert_array_equal(indices[split], second_indices[split])
            self.assertEqual(len(indices[split]), 12)
        keep = sessions != 'right_arm-validation'
        with self.assertRaisesRegex(ValueError, 'three independent sessions'):
            split_sessions(labels[keep], sessions[keep], DEFAULT_LABELS)

    def test_fixed_mapping_preserves_omitted_validation_session_and_original_test_rows(self):
        labels, sessions, mapping = fixture()
        original_indices, _ = split_sessions(labels, sessions, DEFAULT_LABELS, fixed_session_split=mapping)
        keep = sessions != 'right_arm-validation'
        # Also trim one transition row from another train clip, preserving its ID.
        keep[np.flatnonzero(sessions == 'left_arm-train')[0]] = False
        retained_ids = np.flatnonzero(keep)
        indices, assignment = split_sessions(labels[keep], sessions[keep], DEFAULT_LABELS, seed=999,
                                              fixed_session_split=mapping)
        self.assertEqual(assignment, mapping)
        self.assertEqual(assignment['right_arm-validation'], 'validation')
        self.assertEqual(set(sessions[keep][indices['validation']]),
                         {label + '-validation' for label in DEFAULT_LABELS if label != 'right_arm'})
        np.testing.assert_array_equal(retained_ids[indices['test']], original_indices['test'])
        np.testing.assert_array_equal(np.sort(np.concatenate(list(indices.values()))), np.arange(keep.sum()))
        self.assertEqual(len(set(np.concatenate(list(indices.values())))), int(keep.sum()))

    def test_fixed_mapping_requires_known_sessions_and_valid_split_names(self):
        labels, sessions, mapping = fixture()
        for changed in (None, [], {}, mapping | {'unused': 'validation_typo'}, mapping | {'': 'test'}):
            if changed is None:
                continue
            with self.subTest(changed=changed), self.assertRaisesRegex(ValueError, 'Fixed session mapping'):
                split_sessions(labels, sessions, DEFAULT_LABELS, fixed_session_split=changed)
        missing = dict(mapping)
        del missing['standing-train']
        with self.assertRaisesRegex(ValueError, 'missing from the fixed mapping'):
            split_sessions(labels, sessions, DEFAULT_LABELS, fixed_session_split=missing)

    def test_every_action_must_still_have_independent_training_and_test_observations(self):
        labels, sessions, mapping = fixture()
        for split in ('train', 'test'):
            keep = sessions != 'right_arm-' + split
            with self.subTest(split=split), self.assertRaisesRegex(ValueError, 'cover every action class'):
                split_sessions(labels[keep], sessions[keep], DEFAULT_LABELS, fixed_session_split=mapping)
        keep = np.array([mapping[session] != 'validation' for session in sessions])
        with self.assertRaisesRegex(ValueError, 'at least one retained session'):
            split_sessions(labels[keep], sessions[keep], DEFAULT_LABELS, fixed_session_split=mapping)

    def test_one_original_session_cannot_acquire_multiple_action_labels(self):
        labels, sessions, mapping = fixture()
        labels[1] = 'left_arm'
        with self.assertRaisesRegex(ValueError, 'multiple labels'):
            split_sessions(labels, sessions, DEFAULT_LABELS, fixed_session_split=mapping)

    def test_coverage_and_digest_record_missing_validation_class_without_fake_accuracy(self):
        labels, sessions, mapping = fixture()
        keep = sessions != 'right_arm-validation'
        labels, sessions = labels[keep], sessions[keep]
        indices, assignment = split_sessions(labels, sessions, DEFAULT_LABELS, fixed_session_split=mapping)
        details = _split_details(labels, sessions, DEFAULT_LABELS, indices, assignment, True)
        self.assertEqual(details['session_split_mode'], 'fixed')
        self.assertEqual(details['missing_validation_classes'], ['right_arm'])
        self.assertEqual(details['split_coverage']['validation']['right_arm'], {'samples': 0, 'sessions': 0})
        canonical = json.dumps(mapping, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
        self.assertEqual(details['fixed_session_split_sha256'], hashlib.sha256(canonical).hexdigest())
        reverse = dict(reversed(list(mapping.items())))
        same = _split_details(labels, sessions, DEFAULT_LABELS, indices, reverse, True)
        self.assertEqual(details['fixed_session_split_sha256'], same['fixed_session_split_sha256'])
        actual = np.array([DEFAULT_LABELS.index(label) for label in labels[indices['validation']]])
        predictions = actual.copy()
        predictions[actual == 0] = 1
        accuracies = _class_accuracies(actual, predictions, DEFAULT_LABELS)
        self.assertIsNone(accuracies['right_arm'])
        self.assertEqual(accuracies['standing'], 0)
        self.assertEqual(accuracies['left_arm'], 1)
        self.assertIn('"right_arm": null', json.dumps(accuracies))


if __name__ == '__main__':
    unittest.main()
