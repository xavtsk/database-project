-- Caller holds the trainer row lock. Parameters: trainer ID, rolled shiny flag.
SELECT p.id,p.name,p.rarity,COUNT(o.id) AS copies
FROM pokemon p
LEFT JOIN owned_pokemon o ON o.pokemon_id=p.id AND o.trainer_id=%s AND o.is_shiny=%s
GROUP BY p.id,p.name,p.rarity
HAVING p.rarity='legendary' OR COUNT(o.id)<6
ORDER BY p.id;
