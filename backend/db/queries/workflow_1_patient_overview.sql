-- Workflow 1: Patient overview
--
-- Embryologist enters a patient ID and sees one card per embryo with
-- ploidy + live-birth predictions and a blastocyst-stage thumbnail.
-- Cards sort by live-birth score (top embryos first).
--
-- Run:  psql -d embpred -f backend/db/queries/workflow_1_patient_overview.sql
-- Or:   psql -d embpred -v patient_id=patient1 -f .../workflow_1_patient_overview.sql

\set patient_id 'patient1'

SELECT
    pt.external_id                                    AS patient_id,
    pt.name,
    EXTRACT(YEAR FROM AGE(pt.date_of_birth))::int     AS age,
    pt.office,
    e.label                                           AS embryo,
    e.num_timepoints,
    e.date_seeded,
    e.thumbnail_timepoint                             AS thumb_tp,
    img.path                                          AS thumbnail_path,
    pp.ploidy,
    ROUND(pp.score::numeric, 2)                       AS ploidy_score,
    ROUND(lb.score::numeric, 2)                       AS live_birth,
    (
        pp.model_version LIKE 'fabricated-%'
        OR lb.model_version LIKE 'fabricated-%'
    )                                                 AS is_fabricated
FROM patients pt
JOIN embryos e
    ON e.patient_external_id = pt.external_id
LEFT JOIN ploidy_predictions pp
    ON pp.patient_external_id = e.patient_external_id
    AND pp.embryo_label       = e.label
LEFT JOIN live_birth_predictions lb
    ON lb.patient_external_id = e.patient_external_id
    AND lb.embryo_label       = e.label
LEFT JOIN images img
    ON img.patient_external_id = e.patient_external_id
    AND img.embryo_label       = e.label
    AND img.timepoint          = e.thumbnail_timepoint
    AND img.focal_depth        = 0
WHERE pt.external_id = :'patient_id'
ORDER BY lb.score DESC NULLS LAST;
