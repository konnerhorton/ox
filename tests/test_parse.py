"""Tests for parsing functions.

Testing philosophy:
- Focus on the weight_text_to_quantity and process_weights functions
- These are the most error-prone and have known bugs
- Test edge cases from the documentation
"""

import pytest
from ox.parse import weight_text_to_quantity, process_weights
from ox.units import ureg


class TestWeightTextToQuantity:
    """Test parsing individual weight strings.

    This is the lowest-level parsing function.
    """

    def test_parse_kg(self):
        """Test parsing kilogram weights."""
        result = weight_text_to_quantity("24kg")
        assert result == 24 * ureg.kilogram

    def test_parse_lb(self):
        """Test parsing pound weights."""
        result = weight_text_to_quantity("135lb")
        assert result == 135 * ureg.pound

    def test_parse_gram(self):
        """Test parsing gram weights."""
        result = weight_text_to_quantity("500g")
        assert result == 500 * ureg.gram

    def test_parse_ounce(self):
        """Test parsing ounce weights."""
        result = weight_text_to_quantity("16oz")
        assert result == 16 * ureg.ounce

    def test_parse_stone(self):
        """Test parsing stone weights."""
        result = weight_text_to_quantity("12stone")
        assert result == 12 * ureg.stone

    def test_parse_pound_alias(self):
        """Test parsing 'pound' as long-form unit."""
        result = weight_text_to_quantity("135pound")
        assert result == 135 * ureg.pound

    def test_parse_kilogram_alias(self):
        """Test parsing 'kilogram' as long-form unit."""
        result = weight_text_to_quantity("24kilogram")
        assert result == 24 * ureg.kilogram

    def test_parse_decimal_weight(self):
        """Test parsing decimal weights."""
        result = weight_text_to_quantity("2.5kg")
        assert result == 2.5 * ureg.kilogram

    def test_rejects_non_mass_unit(self):
        """Test that non-mass units are rejected."""
        assert weight_text_to_quantity("100m") is None
        assert weight_text_to_quantity("30min") is None

    def test_parse_invalid(self):
        """Test invalid weight strings return None."""
        # No unit
        assert weight_text_to_quantity("100") is None

        # Invalid format
        assert weight_text_to_quantity("abc") is None


class TestProcessWeights:
    """Test parsing weight strings into lists of Quantity objects.

    This handles the complex formats:
    - Single weight: "24kg"
    - Combined weights: "24kg+32kg"
    - Progressive weights: "160/185/210lbs"
    """

    def test_single_weight(self):
        """Single weight is the simplest case."""
        result = process_weights("24kg")

        assert len(result) == 1
        assert result[0] == 24 * ureg.kilogram

    def test_combined_weights(self):
        """Test combined weights (e.g., two kettlebells).

        Example: 24kg+32kg means 56kg total.
        """
        result = process_weights("24kg+32kg")

        assert len(result) == 1
        # Should sum the weights
        assert result[0] == (24 + 32) * ureg.kilogram

    def test_progressive_weights_explicit_units(self):
        """Test progressive weights where each has a unit.

        Example: 24kg/32kg/48kg means three different weights.
        """
        result = process_weights("24kg/32kg/48kg")

        assert len(result) == 3
        assert result[0] == 24 * ureg.kilogram
        assert result[1] == 32 * ureg.kilogram
        assert result[2] == 48 * ureg.kilogram

    @pytest.mark.xfail(reason="Known bug: unit not implied across slashes")
    def test_progressive_weights_implied_unit(self):
        """Test progressive weights with implied unit.

        Example: 160/185/210lbs means three weights, all in lbs.

        This is currently BROKEN - the parser doesn't handle implied units.
        Marking as xfail so we know it's a known issue.
        """
        result = process_weights("160/185/210lb")

        assert len(result) == 3
        assert result[0] == 160 * ureg.pound
        assert result[1] == 185 * ureg.pound
        assert result[2] == 210 * ureg.pound

    def test_combined_and_progressive(self):
        """Test mixing combined and progressive weights.

        Example: 24kg+32kg/48kg+56kg means two combined weights.
        """
        result = process_weights("24kg+32kg/48kg+56kg")

        assert len(result) == 2
        assert result[0] == (24 + 32) * ureg.kilogram
        assert result[1] == (48 + 56) * ureg.kilogram


class TestRepSchemes:
    """Test parsing rep schemes.

    Rep schemes can be:
    - 5x5 means 5 sets of 5 reps
    - 5/5/5 means 3 sets with 5 reps each
    - 5/3/1 means 3 sets with different reps
    """

    # Note: These tests would require importing process_details or a higher-level
    # parsing function. Skipping for now since the main pain point is weights.
    # Can add if needed.

    pass
