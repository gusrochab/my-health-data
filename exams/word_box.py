
class WordBox:
    def __init__(self, text, vertices, center):
        self.text = text
        self.vertices = vertices
        self.center = center

    def __repr__(self):
        return f'{self.text} - {self.vertices}'



