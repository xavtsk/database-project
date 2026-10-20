-- Reusable derived data: no duplicated catalogue values or player state.
CREATE OR REPLACE VIEW v_pokemon_cost AS
SELECT id AS pokemon_id, name,
       CEIL((hp+attack+defense+special_attack+special_defense+speed)/100.0) AS cost
FROM pokemon;

-- Multiply the two defensive slots directly: immunities remain exactly zero.
CREATE OR REPLACE VIEW v_pokemon_defense AS
SELECT pt.pokemon_id, te.attacking_type AS type_id,
       MAX(CASE WHEN pt.slot=1 THEN te.multiplier END)
       * COALESCE(MAX(CASE WHEN pt.slot=2 THEN te.multiplier END),1) AS multiplier
FROM pokemon_types pt
JOIN type_effectiveness te ON te.defending_type=pt.type_id
GROUP BY pt.pokemon_id,te.attacking_type;

-- The same default-move policy used by Team Builder. Users can override it.
CREATE OR REPLACE VIEW v_ranked_default_moves AS
SELECT pm.pokemon_id,m.id AS move_id,m.type_id,
       ROW_NUMBER() OVER (
           PARTITION BY pm.pokemon_id
           ORDER BY (pt.pokemon_id IS NULL),ABS(m.power-70),m.id
       ) AS move_rank
FROM pokemon_moves pm
JOIN moves m ON m.id=pm.move_id
LEFT JOIN pokemon_types pt ON pt.pokemon_id=pm.pokemon_id AND pt.type_id=m.type_id;
