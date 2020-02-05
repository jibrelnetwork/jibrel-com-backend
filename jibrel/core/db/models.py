class CloneMixin:
    def clone(self, attrs: dict = None):
        attrs = attrs or {}
        clone_ = CloneMixin._create_copy_of_instance(self)
        clone_.pk = None
        for name, value in attrs.items():
            setattr(clone_, name, value)
        clone_.save()
        return clone_

    @classmethod
    def _create_copy_of_instance(cls, instance):
        defaults = {}
        fields = instance._meta.concrete_fields

        for f in fields:
            if all([
                not f.auto_created,
                f.concrete,
                f.editable,
                f not in instance._meta.related_objects,
                f not in instance._meta.many_to_many,
            ]):
                value = getattr(instance, f.attname, f.get_default())
                defaults[f.attname] = value

        return instance.__class__(**defaults)
