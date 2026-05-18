-- Workflow 2: Focal scroll view
--
-- For one (embryo, timepoint), return all focal-depth images with the shared
-- bbox crop and morphokinetic stage. Arrow keys scroll the focal axis
-- (rows here, ordered by depth); left/right would change :timepoint.
--
-- Run:  psql -d embpred -f backend/db/queries/workflow_2_focal_scroll.sql

\set patient_id    'patient1'
\set embryo_label  'Emb1'
\set timepoint     521

SELECT
    i.focal_depth,
    i.path,
    b.bbox,
    t.stage,
    e.num_timepoints,
    e.date_seeded,
    e.label AS embryo
FROM images i
JOIN embryos e
    ON e.patient_external_id = i.patient_external_id
    AND e.label              = i.embryo_label
LEFT JOIN bbox_predictions b
    ON b.patient_external_id = i.patient_external_id
    AND b.embryo_label       = i.embryo_label
    AND b.timepoint          = i.timepoint
LEFT JOIN timepoint_predictions t
    ON t.patient_external_id = i.patient_external_id
    AND t.embryo_label       = i.embryo_label
    AND t.timepoint          = i.timepoint
WHERE i.patient_external_id = :'patient_id'
  AND i.embryo_label        = :'embryo_label'
  AND i.timepoint           = :timepoint
ORDER BY i.focal_depth;
