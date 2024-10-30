class BaseConverter:
    def encode(self, i):
        neg, value = self.convert(i, self.decimal_digits, self.digits, "-")
    def decode(self, s):
        neg, value = self.convert(s, self.digits, self.decimal_digits, self.sign)
def convert(self, number, from_digits, to_digits, sign):
