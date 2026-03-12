# Domain Knowledge: Scheduling Service

## 1. System Overview
The scheduling service executes data jobs via Airflow.
- **Job Types**:
  - **SQL**: Executed via `CustomBigQueryOperator`. Uses Python Google Cloud BigQuery client.
  - **Python Notebook**: Executed in a JupyterLab environment on external GKE clusters.

## 2. DAG Infrastructure
A standard DAG follows this lifecycle:
`start` -> `pre_processing` -> `processing` -> `post_processing` -> `completed`

### 2.1 pre_processing
- **Task**: `fin_history_sensor_{table_name}`
- **Logic**: Checks if upstream data has arrived in the target table.
- **Timeout**: **72 hours (3 days)**. Failure here usually means data delay, not a code bug.

### 2.2 processing
- **SQL Job**: Implementation of `CustomBigQueryOperator`.
  - **Rule**: If appending to an existing Mart table, the schema of the query result **MUST** match the target table exactly.
  - **Permissions**: Requires Service Account access to the specific BigQuery Project/Dataset.
- **Notebook Job**: Runs on GKE.
  - **Keywords**: "Pandas", "DataFrame" are common in trace logs.
  - **Logs**: Typically large as the entire traceback from the remote cluster is sent.
- **Global Timeout**: BigQuery single job timeout is **6 hours**.

### 2.3 post_processing
- Updates Policy Tags on BigQuery tables.
- Publishes execution metadata (row counts, partition sizes).
- Triggers downstream jobs via metadata updates.

## 3. Common Failure Patterns
- **BQ_SCHEMA_MISMATCH**: Occurs in Mart table appends.
- **SENSOR_TIMEOUT**: Upstream data didn't arrive within 3 days.
- **GKE_OOM**: Notebook job exceeded memory limits.
- **AUTH_ERROR**: Service account permissions missing.
