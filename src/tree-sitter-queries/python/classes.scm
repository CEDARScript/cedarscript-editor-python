; Class Definitions
(class_definition
    {definition_base}
    {common_body}
) @class.definition

; Decorated Class Definitions
(decorated_definition
    (decorator)+ @class.decorator
    (class_definition
        {definition_base}
        {common_body}
    ) @class.definition
)

; Nested Classes
(class_definition
    body: (block
        (class_definition
            {definition_base}
            {common_body}
        ) @class.definition
    )
)

; Decorated Nested Classes
(class_definition
    body: (block
        (decorated_definition
            (decorator)+ @class.decorator
            (class_definition
                {definition_base}
                {common_body}
            ) @class.definition
        )
    )
)
