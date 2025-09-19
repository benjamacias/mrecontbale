from django.contrib.auth.forms import UserCreationForm

from .models import User


class UserForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "role")
        labels = {
            "username": "Nombre de usuario",
            "email": "Correo electrónico",
            "role": "Rol",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].label = "Contraseña"
        self.fields["password2"].label = "Confirmación de contraseña"

        base_classes = (
            "w-full rounded-xl border border-slate-300 bg-white px-4 py-2 text-slate-700 "
            "shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 "
            "focus:ring-blue-500/50"
        )
        field_attr_map = {
            "username": {
                "placeholder": "Nombre de usuario",
                "autocomplete": "username",
            },
            "email": {
                "placeholder": "correo@empresa.com",
                "autocomplete": "email",
            },
            "role": {},
            "password1": {
                "placeholder": "Contraseña segura",
                "autocomplete": "new-password",
            },
            "password2": {
                "placeholder": "Repetir contraseña",
                "autocomplete": "new-password",
            },
        }

        for name, extra_attrs in field_attr_map.items():
            if name not in self.fields:
                continue
            attrs = {
                "class": base_classes,
                "ng-model": f"vm.formData.{name}",
            }
            if name != "role":
                attrs["ng-model-options"] = "{ debounce: 200 }"
            attrs.update(extra_attrs)
            self.fields[name].widget.attrs.update(attrs)
