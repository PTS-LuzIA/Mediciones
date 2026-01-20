-- Migración: Agregar columna 'orden' a la tabla partidas
-- Fecha: 2026-01-19
-- Descripción: Permite mantener el orden original del PDF en las partidas

-- Verificar si la columna ya existe antes de agregarla
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'v2'
        AND table_name = 'partidas'
        AND column_name = 'orden'
    ) THEN
        ALTER TABLE v2.partidas ADD COLUMN orden INTEGER;
        RAISE NOTICE 'Columna orden agregada exitosamente a v2.partidas';
    ELSE
        RAISE NOTICE 'La columna orden ya existe en v2.partidas';
    END IF;
END $$;
