-- Actualizar longitud del campo unidad en partidas para mayor flexibilidad
-- De VARCHAR(10) a VARCHAR(20) por precaución

DO $$
BEGIN
    -- Modificar columna unidad para soportar hasta 20 caracteres
    ALTER TABLE v2.partidas ALTER COLUMN unidad TYPE VARCHAR(20);

    RAISE NOTICE 'Columna unidad en v2.partidas actualizada a VARCHAR(20)';
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error al actualizar columna: %', SQLERRM;
END $$;
