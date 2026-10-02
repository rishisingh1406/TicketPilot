def evaluate_citation(
    expected_sources: list[str],
    actual_sources: list[str],
    citation_required: bool,
) -> bool | None:
    """
    Evaluate whether the retrieved sources satisfy the
    citation requirement for a golden-set case.

    Returns:
        None:
            Citation is not required for this case.

        True:
            Citation is required and at least one expected source
            was retrieved.

        False:
            Citation is required but none of the expected sources
            were retrieved.
    """

    # --------------------------------------------------------
    # Citation is not required
    # --------------------------------------------------------

    if not citation_required:
        return None

    # --------------------------------------------------------
    # Citation is required
    #
    # Compare sources as sets because retrieval may return
    # multiple chunks from the same or different sources.
    # --------------------------------------------------------

    expected = set(expected_sources)
    actual = set(actual_sources)

    # At least one expected source must be present.
    return bool(expected & actual)


