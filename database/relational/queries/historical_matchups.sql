-- Parameters: installed source, selected Pokemon and selected opponent.
-- Two perspectives preserve first-attacker role instead of sorting participant IDs.
WITH settings AS (SELECT %s AS source_id,%s AS pokemon_id,%s AS opponent_id),
perspectives AS (
    SELECT a.pokemon_id,b.pokemon_id AS opponent_id,'first' AS attacker_role,
           (c.winner_external_id=c.first_external_id) AS won
    FROM settings s JOIN historical_combats c ON c.source_id=s.source_id
    JOIN historical_pokemon a ON a.source_id=c.source_id AND a.external_id=c.first_external_id
    JOIN historical_pokemon b ON b.source_id=c.source_id AND b.external_id=c.second_external_id
    WHERE c.duplicate_of_row IS NULL AND a.mapping_status='matched' AND b.mapping_status='matched'
      AND a.pokemon_id=s.pokemon_id AND b.pokemon_id=s.opponent_id
    UNION ALL
    SELECT b.pokemon_id,a.pokemon_id,'second',
           (c.winner_external_id=c.second_external_id)
    FROM settings s JOIN historical_combats c ON c.source_id=s.source_id
    JOIN historical_pokemon a ON a.source_id=c.source_id AND a.external_id=c.first_external_id
    JOIN historical_pokemon b ON b.source_id=c.source_id AND b.external_id=c.second_external_id
    WHERE c.duplicate_of_row IS NULL AND a.mapping_status='matched' AND b.mapping_status='matched'
      AND b.pokemon_id=s.pokemon_id AND a.pokemon_id=s.opponent_id
)
SELECT pokemon_id,opponent_id,attacker_role,COUNT(*) AS battles,SUM(won) AS wins,
       COUNT(*)-SUM(won) AS losses,SUM(won)/COUNT(*) AS win_rate
FROM perspectives GROUP BY pokemon_id,opponent_id,attacker_role ORDER BY attacker_role;
