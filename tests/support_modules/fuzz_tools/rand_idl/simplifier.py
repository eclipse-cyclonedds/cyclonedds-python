from .containers import RStruct, RUnion, RScope



class SimplifyRStruct:
    def __init__(self, struct: RStruct) -> None:
        self.struct = struct
        self.minimal_err_struct = None
        self._success = True

    def report(self, status: bool) -> None:
        self._success = status

    def _struct(self, *, name=None, scope=None, extensibility=None, fields=None, annotations=None):
        return RStruct(
                name=name or self.struct.name,
                scope=scope or self.struct.scope,
                extensibility=extensibility or self.struct.extensibility,
                fields=fields or self.struct.fields,
                annotations=annotations or self.struct.annotations
            )

    def get_tests(self) -> RStruct:
        keyless = all("key" not in f.annotations for f in self.struct.fields)

        if not keyless:
            # Try the only-key type
            yield self._struct(fields=[f for f in self.struct.fields if "key" in f.annotations])
            if self._success:
                # twas a non-key member
                for entry in self._vary_fields(vary=["key" not in f.annotations for f in self.struct.fields]):
                    yield entry
            else:
                # twas a key-member and the rest doesn't matter!
                self.struct = self._struct(fields=[f for f in self.struct.fields if "key" in f.annotations])
                for entry in self._vary_fields():
                    yield entry

        for entry in self._vary_fields():
            yield entry

    def _vary_fields(self, vary=None):
        vary = vary or [True] * len(self.struct.fields)

        for i in range(len(vary)):
            if not vary[i]:
                continue

            fields = [self.struct.fields[j] for j in range(i) if not vary[j]]
            fields += self.struct.fields[i+1:]

            yield self._struct(fields=fields)

            if self._success:
                break

        start = max(0, i - 1)

        for i in reversed(range(len(vary))):
            if not vary[i]:
                continue

            pre_fields = [self.struct.fields[j] for j in range(start) if not vary[j]]
            post_fields = [self.struct.fields[j] for j in range(i, len(vary)) if not vary[j]]
            fields = pre_fields + self.struct.fields[start:i] + post_fields

            yield self._struct(fields=fields)

            if self._success:
                break

        stop = min(len(vary) - 1, i + 1)
        pre_fields = [self.struct.fields[j] for j in range(start) if not vary[j]]
        post_fields = [self.struct.fields[j] for j in range(i, len(vary)) if not vary[j]]
        fields = pre_fields + self.struct.fields[start:stop] + post_fields
        self.minimal_err_struct = self._struct(fields=fields)
