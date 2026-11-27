-- Approved external 1v1 evidence, separate from application battle state.
CREATE TABLE IF NOT EXISTS historical_sources (
 id INT AUTO_INCREMENT PRIMARY KEY,
 dataset_key VARCHAR(128) NOT NULL UNIQUE,
 source_url VARCHAR(255) NOT NULL,
 license VARCHAR(100) NOT NULL,
 manifest_sha256 CHAR(64) NOT NULL,
 imported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS historical_pokemon (
 source_id INT NOT NULL, external_id SMALLINT NOT NULL,
 original_name VARCHAR(100) NULL,
 mapping_status VARCHAR(30) NOT NULL,
 pokemon_id SMALLINT NULL,
 hp SMALLINT NOT NULL CHECK(hp>0), attack SMALLINT NOT NULL CHECK(attack>0),
 defense SMALLINT NOT NULL CHECK(defense>0), special_attack SMALLINT NOT NULL CHECK(special_attack>0),
 special_defense SMALLINT NOT NULL CHECK(special_defense>0), speed SMALLINT NOT NULL CHECK(speed>0),
 type_1 VARCHAR(20) NOT NULL, type_2 VARCHAR(20) NULL,
 PRIMARY KEY(source_id,external_id), UNIQUE(source_id,pokemon_id),
 FOREIGN KEY(source_id) REFERENCES historical_sources(id),
 FOREIGN KEY(pokemon_id) REFERENCES pokemon(id),
 CHECK(external_id>0),
 CHECK(mapping_status IN ('matched','outside_catalogue_or_form','missing_name')),
 CHECK((mapping_status='matched' AND pokemon_id IS NOT NULL)
    OR (mapping_status<>'matched' AND pokemon_id IS NULL))
);

CREATE TABLE IF NOT EXISTS historical_combats (
 source_id INT NOT NULL, source_row INT NOT NULL,
 first_external_id SMALLINT NOT NULL, second_external_id SMALLINT NOT NULL,
 winner_external_id SMALLINT NOT NULL, duplicate_of_row INT NULL,
 PRIMARY KEY(source_id,source_row),
 FOREIGN KEY(source_id,first_external_id) REFERENCES historical_pokemon(source_id,external_id),
 FOREIGN KEY(source_id,second_external_id) REFERENCES historical_pokemon(source_id,external_id),
 FOREIGN KEY(source_id,winner_external_id) REFERENCES historical_pokemon(source_id,external_id),
 FOREIGN KEY(source_id,duplicate_of_row) REFERENCES historical_combats(source_id,source_row),
 CHECK(source_row>0), CHECK(first_external_id<>second_external_id),
 CHECK(winner_external_id IN (first_external_id,second_external_id)),
 CHECK(duplicate_of_row IS NULL OR duplicate_of_row<source_row),
 CONSTRAINT historical_duplicate_positive CHECK(duplicate_of_row IS NULL OR duplicate_of_row>0)
);
