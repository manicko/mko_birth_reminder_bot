__all__= ["ColumnMismatch", "ReadCSVError", "WrongInput"]
class ColumnMismatch(Exception):
    pass

class ReadCSVError(Exception):
    pass

class WrongInput(Exception):
    pass
