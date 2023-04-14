class SpliceAIAPIException(Exception):
 
    # Constructor or Initializer
    def __init__(self, message, details):
        self.message = message
        self.details = details
 
    # __str__ is to print() the value
    def __str__(self):
        return(f"{repr(self.message)} ({repr(self.details)})")