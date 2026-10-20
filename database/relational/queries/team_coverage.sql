SELECT t.name AS type,COALESCE(MAX(te.multiplier),0) AS best_multiplier
FROM types t
LEFT JOIN (
    SELECT DISTINCT m.type_id FROM team_member_moves mm
    JOIN moves m ON m.id=mm.move_id WHERE mm.team_id=%s
) mt ON TRUE
LEFT JOIN type_effectiveness te ON te.attacking_type=mt.type_id AND te.defending_type=t.id
GROUP BY t.id,t.name ORDER BY t.id;
