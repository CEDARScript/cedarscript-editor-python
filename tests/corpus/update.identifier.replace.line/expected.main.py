def _check_raw_id_fields_item(obj, field_name, label):
    """Check an item of `raw_id_fields`, i.e. check that field named
    `field_name` exists in model `model` and is a ForeignKey or a
    ManyToManyField."""
