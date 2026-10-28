"""Unit tests for synthetic data generator and ground-truth isolation."""

from deduplication.generator.synthetic_data import (
    generate_customer_dataset,
    generate_product_dataset,
)


def test_generator_fixed_seed_determinism():
    records1, gt1 = generate_customer_dataset(count=50, seed=123)
    records2, gt2 = generate_customer_dataset(count=50, seed=123)

    assert records1 == records2
    assert gt1 == gt2


def test_ground_truth_isolation():
    """Verify that generated records do NOT leak ground-truth cluster labels into input data."""
    records, gt = generate_customer_dataset(count=50, seed=42)

    # Check that each record only contains expected source schema fields
    for r in records:
        assert "cluster_id" not in r
        assert "ground_truth" not in r
        assert "is_duplicate" not in r

    # Check that ground-truth dictionary contains duplicate mappings
    assert len(gt) > 0
    multi_member_clusters = [members for members in gt.values() if len(members) > 1]
    assert len(multi_member_clusters) > 0, "No duplicate clusters were generated!"


def test_product_generator_determinism():
    records1, gt1 = generate_product_dataset(count=50, seed=42)
    records2, gt2 = generate_product_dataset(count=50, seed=42)

    assert records1 == records2
    assert gt1 == gt2

