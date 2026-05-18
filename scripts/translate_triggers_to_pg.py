"""Fase 2 migracion PG · traduce los 42 triggers SQLite a plpgsql.

38 triggers son guardas `BEGIN SELECT RAISE(ABORT,'msg'); END` · se
traducen automaticamente a una funcion plpgsql que hace RAISE EXCEPTION.
4 triggers especiales (updated_at automaticos + audit insert) se portan
con plpgsql escrito a mano.

SQLite -> PostgreSQL:
  SELECT RAISE(ABORT,'msg')   -> RAISE EXCEPTION 'msg'
  WHEN <cond>                 -> IF <cond> THEN ... END IF dentro de la funcion
  X IS NOT NEW.y / OLD.y      -> X IS DISTINCT FROM NEW.y / OLD.y
  AFTER UPDATE + UPDATE self  -> BEFORE UPDATE que setea NEW.col

Uso:  python scripts/translate_triggers_to_pg.py
Salida:  C:/Users/sebas/pgdev/pg_triggers.sql
"""
import re

SRC = 'C:/Users/sebas/pgdev/triggers_to_port.sql'
OUT = 'C:/Users/sebas/pgdev/pg_triggers.sql'

_RAISE = re.compile(
    r"CREATE\s+TRIGGER\s+(\w+)\s+"
    r"(BEFORE|AFTER)\s+(INSERT|UPDATE|DELETE)"
    r"(\s+OF\s+[\w\s,]+?)?"
    r"\s+ON\s+(\w+)\s*"
    r"(?:FOR\s+EACH\s+ROW)?\s*"
    r"(?:WHEN\s+(.+?))?\s*"
    r"BEGIN\s+SELECT\s+RAISE\(ABORT,\s*'(.+?)'\s*\)\s*;\s*END",
    re.I | re.S,
)

# Triggers no-RAISE · plpgsql escrito a mano.
ESPECIALES = {
    'trg_usuarios_identidad_updated_at': """
CREATE OR REPLACE FUNCTION fn_trg_usuarios_identidad_updated_at() RETURNS trigger AS $$
BEGIN
  NEW.updated_at := to_char(now(),'YYYY-MM-DD HH24:MI:SS');
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_usuarios_identidad_updated_at
  BEFORE UPDATE ON usuarios_identidad FOR EACH ROW
  EXECUTE FUNCTION fn_trg_usuarios_identidad_updated_at();
""",
    'trg_mbr_templates_updated_at': """
CREATE OR REPLACE FUNCTION fn_trg_mbr_templates_updated_at() RETURNS trigger AS $$
BEGIN
  IF NEW.updated_at_utc IS NOT DISTINCT FROM OLD.updated_at_utc THEN
    NEW.updated_at_utc := to_char((now() AT TIME ZONE 'UTC'),'YYYY-MM-DD HH24:MI:SS');
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_mbr_templates_updated_at
  BEFORE UPDATE ON mbr_templates FOR EACH ROW
  EXECUTE FUNCTION fn_trg_mbr_templates_updated_at();
""",
    'trg_pedidos_b2b_updated': """
CREATE OR REPLACE FUNCTION fn_trg_pedidos_b2b_updated() RETURNS trigger AS $$
BEGIN
  IF NEW.actualizado_at_utc IS NOT DISTINCT FROM OLD.actualizado_at_utc THEN
    NEW.actualizado_at_utc := to_char((now() AT TIME ZONE 'UTC'),'YYYY-MM-DD HH24:MI:SS');
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_pedidos_b2b_updated
  BEFORE UPDATE ON pedidos_b2b FOR EACH ROW
  EXECUTE FUNCTION fn_trg_pedidos_b2b_updated();
""",
    'trg_op_fija_audit': """
CREATE OR REPLACE FUNCTION fn_trg_op_fija_audit() RETURNS trigger AS $$
BEGIN
  IF OLD.fija_en_dispensacion IS DISTINCT FROM NEW.fija_en_dispensacion THEN
    INSERT INTO operarios_fija_audit (operario_id, valor_anterior, valor_nuevo)
    VALUES (NEW.id, OLD.fija_en_dispensacion, NEW.fija_en_dispensacion);
  END IF;
  RETURN NULL;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_op_fija_audit
  AFTER UPDATE OF fija_en_dispensacion ON operarios_planta FOR EACH ROW
  EXECUTE FUNCTION fn_trg_op_fija_audit();
""",
}


def traducir_cond(cond: str) -> str:
    """Traduce una condicion WHEN de SQLite a SQL de Postgres."""
    c = ' '.join(cond.split())  # colapsar espacios/saltos de linea
    # `X IS NOT NEW.y` / `X IS NOT OLD.y` -> `IS DISTINCT FROM`
    c = re.sub(r'IS\s+NOT\s+(NEW\.|OLD\.)', r'IS DISTINCT FROM \1', c, flags=re.I)
    return c


def traducir_raise(m) -> str:
    name, timing, event, of_cl, table, when, msg = m.groups()
    timing, event = timing.upper(), event.upper()
    of_cl = (of_cl or '').strip()
    of_cl = (' ' + ' '.join(of_cl.split())) if of_cl else ''
    msg = msg.replace("'", "''").replace('%', '%%')
    ret = 'OLD' if event == 'DELETE' else 'NEW'

    if when:
        cond = traducir_cond(when)
        cuerpo = (f"  IF {cond} THEN\n"
                  f"    RAISE EXCEPTION '{msg}';\n"
                  f"  END IF;")
    else:
        cuerpo = f"  RAISE EXCEPTION '{msg}';"

    return (
        f"CREATE OR REPLACE FUNCTION fn_{name}() RETURNS trigger AS $$\n"
        f"BEGIN\n{cuerpo}\n  RETURN {ret};\nEND $$ LANGUAGE plpgsql;\n"
        f"CREATE OR REPLACE TRIGGER {name}\n"
        f"  {timing} {event}{of_cl} ON {table} FOR EACH ROW\n"
        f"  EXECUTE FUNCTION fn_{name}();\n"
    )


def main():
    with open(SRC, encoding='utf-8') as f:
        contenido = f.read()

    # separar por marcador "-- [trigger] nombre"
    partes = re.split(r'^-- \[trigger\] (\w+)$', contenido, flags=re.M)
    salida = ['-- Triggers PostgreSQL de EOS · generado por translate_triggers_to_pg.py\n']
    n_auto = n_esp = 0
    i = 1
    while i + 1 <= len(partes) - 1:
        nombre = partes[i].strip()
        sql = partes[i + 1].strip()
        if nombre in ESPECIALES:
            salida.append(ESPECIALES[nombre].strip() + '\n')
            n_esp += 1
        else:
            m = _RAISE.search(sql)
            if not m:
                raise SystemExit(f'NO pude parsear el trigger {nombre}:\n{sql}')
            salida.append(traducir_raise(m))
            n_auto += 1
        i += 2

    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(salida))

    print(f'OK · {n_auto} triggers RAISE traducidos + {n_esp} especiales -> pg_triggers.sql')


if __name__ == '__main__':
    main()
