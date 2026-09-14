"""Planning helpers.

This package must never import pca.tools. The planner works with tool NAMES
only; turning a name into a callable is the broker's job alone, and that
separation is what makes the policy check unskippable. Enforced by
tests/test_architecture.py.
"""
