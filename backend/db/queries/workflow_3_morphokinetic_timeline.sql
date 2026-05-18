-- Workflow 3: Morphokinetic timeline
--
-- Per embryo, a horizontal timeline of timepoints labeled with their stage.
-- Two result sets:
--   (a) full stream — every timepoint with its stage (for the bar render)
--   (b) milestones  — first occurrence of each stage (for compact labels)
--
-- Run:  psql -d embpred -f backend/db/queries/workflow_3_morphokinetic_timeline.sql

\set patient_id    'patient1'
\set embryo_label  'Emb1'

-- (a) Full stream
SELECT timepoint, stage
FROM timepoint_predictions
WHERE patient_external_id = :'patient_id'
  AND embryo_label        = :'embryo_label'
ORDER BY timepoint;

-- (b) Stage milestones
SELECT
    stage,
    MIN(timepoint) AS first_seen,
    COUNT(*)       AS frames_at_stage
FROM timepoint_predictions
WHERE patient_external_id = :'patient_id'
  AND embryo_label        = :'embryo_label'
GROUP BY stage
ORDER BY MIN(timepoint);
