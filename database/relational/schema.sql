-- Approved prototype schema. Initialization creates missing objects only.
CREATE TABLE IF NOT EXISTS pokemon (
 id SMALLINT PRIMARY KEY, name VARCHAR(40) NOT NULL UNIQUE,
 hp SMALLINT NOT NULL CHECK(hp>0), attack SMALLINT NOT NULL CHECK(attack>0),
 defense SMALLINT NOT NULL CHECK(defense>0), special_attack SMALLINT NOT NULL CHECK(special_attack>0),
 special_defense SMALLINT NOT NULL CHECK(special_defense>0), speed SMALLINT NOT NULL CHECK(speed>0),
 rarity VARCHAR(12) NOT NULL CHECK(rarity IN ('common','uncommon','rare','legendary')),
 description TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS types (id SMALLINT PRIMARY KEY, name VARCHAR(20) NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS pokemon_types (
 pokemon_id SMALLINT NOT NULL, type_id SMALLINT NOT NULL, slot TINYINT NOT NULL CHECK(slot BETWEEN 1 AND 2),
 PRIMARY KEY(pokemon_id,slot), UNIQUE(pokemon_id,type_id),
 FOREIGN KEY(pokemon_id) REFERENCES pokemon(id), FOREIGN KEY(type_id) REFERENCES types(id)
);
CREATE TABLE IF NOT EXISTS moves (
 id SMALLINT PRIMARY KEY, name VARCHAR(60) NOT NULL UNIQUE, type_id SMALLINT NOT NULL,
 damage_class VARCHAR(10) NOT NULL CHECK(damage_class IN ('physical','special')),
 power SMALLINT NOT NULL CHECK(power>0), accuracy SMALLINT NULL CHECK(accuracy BETWEEN 0 AND 100),
 pp SMALLINT NOT NULL CHECK(pp>0), priority SMALLINT NOT NULL,
 FOREIGN KEY(type_id) REFERENCES types(id)
);
CREATE TABLE IF NOT EXISTS pokemon_moves (
 pokemon_id SMALLINT NOT NULL, move_id SMALLINT NOT NULL,
 source VARCHAR(20) NOT NULL CHECK(source IN ('raw','project_override')),
 PRIMARY KEY(pokemon_id,move_id), FOREIGN KEY(pokemon_id) REFERENCES pokemon(id),
 FOREIGN KEY(move_id) REFERENCES moves(id)
);
CREATE TABLE IF NOT EXISTS type_effectiveness (
 attacking_type SMALLINT NOT NULL, defending_type SMALLINT NOT NULL,
 multiplier DECIMAL(3,2) NOT NULL CHECK(multiplier IN (0,0.5,1,2)),
 PRIMARY KEY(attacking_type,defending_type), FOREIGN KEY(attacking_type) REFERENCES types(id),
 FOREIGN KEY(defending_type) REFERENCES types(id)
);
CREATE TABLE IF NOT EXISTS trainers (
 id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(40) NOT NULL,
 starter_chosen BOOLEAN NOT NULL DEFAULT FALSE, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS owned_pokemon (
 id INT AUTO_INCREMENT PRIMARY KEY, trainer_id INT NOT NULL, pokemon_id SMALLINT NOT NULL,
 source VARCHAR(12) NOT NULL CHECK(source IN ('starter','reward')),
 acquired_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(id,trainer_id), FOREIGN KEY(trainer_id) REFERENCES trainers(id),
 FOREIGN KEY(pokemon_id) REFERENCES pokemon(id)
);
CREATE TABLE IF NOT EXISTS teams (
 id INT AUTO_INCREMENT PRIMARY KEY, trainer_id INT NOT NULL, name VARCHAR(60) NOT NULL,
 UNIQUE(id,trainer_id), FOREIGN KEY(trainer_id) REFERENCES trainers(id)
);
CREATE TABLE IF NOT EXISTS team_members (
 team_id INT NOT NULL, slot TINYINT NOT NULL CHECK(slot BETWEEN 1 AND 6),
 owned_id INT NOT NULL, trainer_id INT NOT NULL,
 PRIMARY KEY(team_id,slot), UNIQUE(team_id,owned_id),
 FOREIGN KEY(team_id,trainer_id) REFERENCES teams(id,trainer_id) ON DELETE CASCADE,
 FOREIGN KEY(owned_id,trainer_id) REFERENCES owned_pokemon(id,trainer_id)
);
CREATE TABLE IF NOT EXISTS team_member_moves (
 team_id INT NOT NULL, member_slot TINYINT NOT NULL,
 move_slot TINYINT NOT NULL CHECK(move_slot BETWEEN 1 AND 4), move_id SMALLINT NOT NULL,
 PRIMARY KEY(team_id,member_slot,move_slot), UNIQUE(team_id,member_slot,move_id),
 FOREIGN KEY(team_id,member_slot) REFERENCES team_members(team_id,slot) ON DELETE CASCADE,
 FOREIGN KEY(move_id) REFERENCES moves(id)
);
CREATE TABLE IF NOT EXISTS battle_rewards (
 battle_id CHAR(36) PRIMARY KEY, trainer_id INT NOT NULL, owned_id INT NOT NULL UNIQUE,
 rarity VARCHAR(12) NOT NULL, roll DECIMAL(10,8) NOT NULL,
 created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(trainer_id) REFERENCES trainers(id), FOREIGN KEY(owned_id) REFERENCES owned_pokemon(id)
);
