# Verified Python test results

These saved outputs record successful runs from the November 2026 project verification session. The separate integration run completed on 12 November 2026 against MySQL 8.4.13 and MongoDB Atlas.

| Evidence | Collected | Passed | Skipped | Duration |
| --- | ---: | ---: | ---: | ---: |
| [Query tests](query-test-results.txt) | 15 | 15 | 0 | 110.182 s |
| [Broader suite](full-test-results.txt) | 124 | 115 | 9 | 210.787 s |
| [Separate integration tests](integration-test-results.txt) | 9 | 9 | 0 | 293.298 s |

The nine integration tests are the nine skipped in the broader run. All 124 Python tests therefore passed across two runs. The query tests overlap the broader suite and must not be added to that total. This is not evidence of one combined 124-test run or an independent clean-machine installation.

## Reproducing the checks

Run from the repository root in Command Prompt with the configured databases reachable. For query checks, use the regular project credentials:

```bat
set "RUN_DB_TESTS="
set "RUN_QUERY_TESTS=1"
python -m unittest tests.test_database_queries tests.test_historical_queries -v
python -m unittest discover -s tests -v
```

For the separate integration checks, use a dedicated SQL test account with privileges limited to `pokedex_test_` databases. Set its credentials privately in the test terminal, then run:

```bat
set "RUN_DB_TESTS=1"
python -m unittest tests.test_app_integration -v
```

The integration tests load `.env` connection settings while preserving explicit terminal overrides, create a unique temporary SQL database, and remove it after successful execution. MongoDB fixtures use unique database names within the Atlas length limit and remove their temporary `battles` collections during cleanup. Query fixtures roll back SQL changes. A setup failure can leave a temporary test database requiring later inspection; do not delete the application database.

Keep credentials, private SSH files and terminal password entry out of committed evidence. The original saved outputs are retained here without altering their test results.
