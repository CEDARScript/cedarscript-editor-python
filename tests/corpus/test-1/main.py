class A:
    def _calc(self, a):
        return a
    def _check(self, a: int, b, c):
        if a > 0:
            return self._calc(
                "a thing or two"
            )
        else:
            return list(
                self._calc(
                    self._candidate(
                        a, "string 1", 4
                    )
                    for index, item in enumerate(a.the_elements)
                )
            )

    def _candidate(self, a, b, c):
        return a
