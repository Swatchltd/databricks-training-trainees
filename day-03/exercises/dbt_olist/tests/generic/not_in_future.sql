-- Custom GENERIC test (a macro): a timestamp column must not be in the future.
-- Reusable from any model's YAML:  tests: [not_in_future]
-- Passes when this query returns 0 rows (i.e. no failing rows).
{% test not_in_future(model, column_name) %}

    select {{ column_name }} from {{ model }} where {{ column_name }} > current_timestamp()

{% endtest %}
