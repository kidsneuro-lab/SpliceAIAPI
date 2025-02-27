class SpliceAIAPIException(Exception):
 
    # Constructor or Initializer
    def __init__(self, summary: str, details: str = None):
        self.summary = summary
        self.details = details
 
    # __str__ is to print() the value
    def __str__(self):
        return(f"{repr(self.summary)} ({repr(self.details)})")