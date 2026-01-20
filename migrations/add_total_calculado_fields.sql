-- Agregar campos total_calculado a capítulos y subcapítulos para Fase 3
-- Estos campos guardarán los totales calculados sumando partidas
-- mientras que 'total' mantiene el valor original del PDF

DO $$
BEGIN
    -- Agregar total_calculado a capitulos
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'v2' AND table_name = 'capitulos' AND column_name = 'total_calculado'
    ) THEN
        ALTER TABLE v2.capitulos ADD COLUMN total_calculado NUMERIC(14, 2);
        RAISE NOTICE 'Columna total_calculado agregada a v2.capitulos';
    END IF;

    -- Agregar total_calculado a subcapitulos
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'v2' AND table_name = 'subcapitulos' AND column_name = 'total_calculado'
    ) THEN
        ALTER TABLE v2.subcapitulos ADD COLUMN total_calculado NUMERIC(14, 2);
        RAISE NOTICE 'Columna total_calculado agregada a v2.subcapitulos';
    END IF;
END $$;
