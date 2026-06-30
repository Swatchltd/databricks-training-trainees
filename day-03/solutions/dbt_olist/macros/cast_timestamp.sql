{#- Reusable timestamp cast with optional alias. Keeps staging DRY. -#}
{%- macro cast_timestamp(column_name, alias=none) -%}
    try_cast({{ column_name }} as timestamp) {%- if alias is not none %} as {{ alias }}{%- endif -%}
{%- endmacro -%}
