class DBRow:

    TABLENAME = ""

    PRIMARY_KEY_COLUMNS = None
    # cant assign [] here otherwise col names of all subclasses will be appended to same list
    COLUMNS = None
    ASSOCIATED_COLUMNS = None

    def __init__(self, manga_db, **kwargs):
        self.manga_db = manga_db
        # commited values get added when col gets modified
        self._committed_state = {}
        # gets set to true when loaded from db through load_instance
        self._in_db = False

    @property
    def key(self):
        return self.__class__, tuple((getattr(self, col) for col in self.PRIMARY_KEY_COLUMNS))

    @classmethod
    def from_dict(cls, manga_db, dic):
        # only update fields that are in cls.get_column_names()
        row = cls(manga_db)
        row.__dict__.update(cls.filter_dict(dic))

    @classmethod
    def get_all_column_names(cls):
        """
        Returns list of strings containing all column names
        """
        return cls.COLUMNS + cls.ASSOCIATED_COLUMNS

    @classmethod
    def filter_dict(cls, data):
        """
        Filters out all data fields that are not in cls.get_column_names()
        """
        dic = {}
        for col in cls.get_column_names():
            try:
                dic[col] = data[col]
            except KeyError:
                pass
        return dic

    def export_for_db(self):
        """
        Returns a dict with all the attributes of self that are stored in the row directly
        """
        result = {}
        for attr in self.COLUMNS:
            val = getattr(self, attr)
            if (attr in self.NOT_NULL_COLS) and val is None:
                raise ValueError(f"'self.{attr}' can't be NULL when exporting for DB!")
            result[attr] = val
        return result

    def save(self):
        """
        Save changes to DB
        """
        raise NotImplementedError

    def diff_normal_cols(self, row):
        changed_str = []
        changed_cols = []
        for col in self.COLUMNS:
            self_attr = getattr(self, col)
            if row[col] != self_attr:
                changed_str.append(f"Column '{col}' changed from '{row[col]}' to '{self_attr}'")
                changed_cols.append(col)
        return "\n".join(changed_str), changed_cols

    def __repr__(self):
        selfdict_str = ", ".join((f"{attr}: '{val}'" for attr, val in self.__dict__.items()))
        return f"{self.__class__.__name__}({selfdict_str})"
