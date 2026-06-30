{#- English category name, falling back to Portuguese, then 'unknown'. -#}
{%- macro generate_category_label(english_col, portuguese_col) -%}
    coalesce({{ english_col }}, {{ portuguese_col }}, 'unknown')
{%- endmacro -%}
