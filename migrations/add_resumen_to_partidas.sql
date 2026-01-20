-- Agregar campo resumen a partidas
-- El resumen es el título corto de la partida, mientras que descripcion es más detallada

DO $$
BEGIN
    -- Agregar resumen a partidas
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'v2' AND table_name = 'partidas' AND column_name = 'resumen'
    ) THEN
        ALTER TABLE v2.partidas ADD COLUMN resumen VARCHAR(500);
        RAISE NOTICE 'Columna resumen agregada a v2.partidas';
    END IF;
END $$;
