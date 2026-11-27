SELECT t.name,
       COALESCE(SUM(d.multiplier>1),0) AS weak,
       COALESCE(SUM(d.multiplier>2),0) AS double_weak,
       COALESCE(SUM(d.multiplier>0 AND d.multiplier<1),0) AS resistant,
       COALESCE(SUM(d.multiplier=0),0) AS immune
FROM types t
LEFT JOIN (SELECT o.pokemon_id FROM team_members tm JOIN owned_pokemon o ON o.id=tm.owned_id
           WHERE tm.team_id=%s) r ON TRUE
LEFT JOIN v_pokemon_defense d ON d.pokemon_id=r.pokemon_id AND d.type_id=t.id
GROUP BY t.id,t.name ORDER BY t.id;
