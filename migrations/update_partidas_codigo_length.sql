-- Actualizar longitud del campo codigo en partidas de VARCHAR(10) a VARCHAR(50)
-- Para soportar códigos más largos como m23U02BZ020

DO $$
BEGIN
    -- Modificar columna codigo para soportar hasta 50 caracteres
    ALTER TABLE v2.partidas ALTER COLUMN codigo TYPE VARCHAR(50);

    RAISE NOTICE 'Columna codigo en v2.partidas actualizada a VARCHAR(50)';
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error al actualizar columna: %', SQLERRM;
END $$;
