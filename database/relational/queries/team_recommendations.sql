-- Parameters: trainer ID, team ID, point limit. All scoring/ranking happens here.
WITH
settings AS (SELECT %s AS trainer_id,%s AS team_id,%s AS point_limit),
roster AS (
    SELECT tm.owned_id,tm.slot,o.pokemon_id,pc.cost,pc.name
    FROM settings s JOIN teams t ON t.id=s.team_id AND t.trainer_id=s.trainer_id
    JOIN team_members tm ON tm.team_id=t.id
    JOIN owned_pokemon o ON o.id=tm.owned_id
    JOIN v_pokemon_cost pc ON pc.pokemon_id=o.pokemon_id
),
baseline AS (SELECT COUNT(*) AS team_size,COALESCE(SUM(cost),0) AS total_cost FROM roster),
baseline_weaknesses AS (
    SELECT t.id,t.name,
           COALESCE(SUM(GREATEST(d.multiplier-1,0)),0) AS exposure_sum
    FROM types t LEFT JOIN roster r ON TRUE
    LEFT JOIN v_pokemon_defense d ON d.pokemon_id=r.pokemon_id AND d.type_id=t.id
    GROUP BY t.id,t.name
),
current_move_types AS (
    SELECT DISTINCT r.owned_id,m.type_id
    FROM roster r JOIN settings s ON TRUE
    JOIN team_member_moves mm ON mm.team_id=s.team_id AND mm.member_slot=r.slot
    JOIN moves m ON m.id=mm.move_id
),
baseline_coverage AS (
    SELECT t.id,t.name,COALESCE(MAX(te.multiplier),0) AS multiplier
    FROM types t LEFT JOIN current_move_types mt ON TRUE
    LEFT JOIN type_effectiveness te ON te.attacking_type=mt.type_id AND te.defending_type=t.id
    GROUP BY t.id,t.name
),
baseline_defense_score AS (
    SELECT SUM(w.exposure_sum)*1E0/NULLIF(b.team_size,0) AS before_exposure,
           JSON_OBJECTAGG(w.name,w.exposure_sum*1E0/NULLIF(b.team_size,0)) AS before_weaknesses
    FROM baseline_weaknesses w CROSS JOIN baseline b GROUP BY b.team_size
),
baseline_attack_score AS (
    SELECT SUM(multiplier>1) AS before_coverage,JSON_OBJECTAGG(name,multiplier) AS before_coverage_types
    FROM baseline_coverage
),
candidates AS (
    SELECT o.id AS owned_id,o.pokemon_id,pc.name,pc.cost
    FROM settings s JOIN owned_pokemon o ON o.trainer_id=s.trainer_id
    JOIN v_pokemon_cost pc ON pc.pokemon_id=o.pokemon_id
    WHERE NOT EXISTS (SELECT 1 FROM roster r WHERE r.owned_id=o.id)
),
plans AS (
    SELECT c.*,r.owned_id AS replace_owned_id,r.pokemon_id AS replace_pokemon_id,r.name AS replace_name,
           b.total_cost+c.cost-COALESCE(r.cost,0) AS proposed_cost,
           CASE WHEN b.team_size=6 THEN 6 ELSE b.team_size+1 END AS proposed_size
    FROM candidates c CROSS JOIN baseline b LEFT JOIN roster r ON b.team_size=6
),
affordable AS (SELECT p.* FROM plans p CROSS JOIN settings s WHERE p.proposed_cost<=s.point_limit),
plan_defense AS (
    SELECT p.owned_id,p.replace_owned_id,w.name,
           (w.exposure_sum+GREATEST(d.multiplier-1,0)-COALESCE(GREATEST(old.multiplier-1,0),0))
           *1E0/p.proposed_size AS exposure
    FROM affordable p CROSS JOIN baseline_weaknesses w
    JOIN v_pokemon_defense d ON d.pokemon_id=p.pokemon_id AND d.type_id=w.id
    LEFT JOIN v_pokemon_defense old ON old.pokemon_id=p.replace_pokemon_id AND old.type_id=w.id
),
plan_defense_scores AS (
    SELECT owned_id,replace_owned_id,SUM(exposure) AS after_exposure,
           JSON_OBJECTAGG(name,exposure) AS after_weaknesses
    FROM plan_defense GROUP BY owned_id,replace_owned_id
),
proposed_move_types AS (
    SELECT p.owned_id,p.replace_owned_id,m.type_id
    FROM affordable p JOIN current_move_types m ON p.replace_owned_id IS NULL OR m.owned_id<>p.replace_owned_id
    UNION
    SELECT p.owned_id,p.replace_owned_id,m.type_id
    FROM affordable p JOIN v_ranked_default_moves m ON m.pokemon_id=p.pokemon_id AND m.move_rank<=4
),
plan_coverage AS (
    SELECT p.owned_id,p.replace_owned_id,t.name,COALESCE(MAX(te.multiplier),0) AS multiplier
    FROM affordable p CROSS JOIN types t
    LEFT JOIN proposed_move_types mt ON mt.owned_id=p.owned_id AND mt.replace_owned_id<=>p.replace_owned_id
    LEFT JOIN type_effectiveness te ON te.attacking_type=mt.type_id AND te.defending_type=t.id
    GROUP BY p.owned_id,p.replace_owned_id,t.id,t.name
),
plan_attack_scores AS (
    SELECT owned_id,replace_owned_id,SUM(multiplier>1) AS after_coverage,
           JSON_OBJECTAGG(name,multiplier) AS after_coverage_types
    FROM plan_coverage GROUP BY owned_id,replace_owned_id
),
scored AS (
    SELECT p.*,d.after_exposure,d.after_weaknesses,a.after_coverage,a.after_coverage_types,
           CASE WHEN b.team_size=0 THEN 0 ELSE bd.before_exposure-d.after_exposure END AS exposure_reduction,
           a.after_coverage-ba.before_coverage AS coverage_gain,b.team_size
    FROM affordable p JOIN plan_defense_scores d ON d.owned_id=p.owned_id AND d.replace_owned_id<=>p.replace_owned_id
    JOIN plan_attack_scores a ON a.owned_id=p.owned_id AND a.replace_owned_id<=>p.replace_owned_id
    CROSS JOIN baseline b CROSS JOIN baseline_defense_score bd CROSS JOIN baseline_attack_score ba
),
improving AS (
    SELECT * FROM scored WHERE team_size=0 OR exposure_reduction>0.000000001
       OR (ABS(exposure_reduction)<=0.000000001 AND coverage_gain>0)
),
species_choices AS (
    SELECT i.*,ROW_NUMBER() OVER (
        PARTITION BY pokemon_id
        ORDER BY ROUND(exposure_reduction,9) DESC,coverage_gain DESC,cost,owned_id,replace_owned_id
    ) AS species_rank FROM improving i
),
ranked AS (
    SELECT c.*,ROW_NUMBER() OVER (
        ORDER BY ROUND(exposure_reduction,9) DESC,coverage_gain DESC,cost,owned_id,replace_owned_id
    ) AS recommendation_rank FROM species_choices c WHERE species_rank=1
)
-- Keep one baseline row even when there are no qualifying suggestions.
SELECT b.team_size AS baseline_size,b.total_cost,bd.before_exposure,bd.before_weaknesses,
       ba.before_coverage,ba.before_coverage_types,r.*
FROM baseline b CROSS JOIN baseline_defense_score bd CROSS JOIN baseline_attack_score ba
LEFT JOIN ranked r ON r.recommendation_rank<=3
ORDER BY r.recommendation_rank;
