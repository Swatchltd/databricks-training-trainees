{#
  Use the custom schema name AS-IS (staging / intermediate / marts) instead of dbt's
  default behaviour, which prefixes it: {{ target.schema }}_{{ custom_schema }}.
  Isolation between people/environments comes from the CATALOG (set per target in
  profiles.yml), so schema names stay identical across local / dev / prod.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%} {{ target.schema }}
    {%- else -%} {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
