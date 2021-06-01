"""

TODO:
    - docstrings
    - arrow navigation of dropdown menu
    - button to remove item
    - button to add new item
"""

# stdlib
from copy import deepcopy
from collections import (namedtuple, Counter,
                         deque as deck,)
# pypi
from qtpy.QtSvg import QSvgRenderer
from qtpy.QtGui import QIcon, QPainter, QPixmap
from qtpy.QtWidgets import QComboBox, QCompleter, QLabel
from qtpy.QtCore import QStringListModel, QObject
# local
from pycuties.icons import clock
# type hints
from typing import (Union as T_Union,
                    List as List_T,
                    Deque as Deck_T)


# --- Utility ---

Previous = namedtuple('Item', ('index', 'text'))


def find_indices_to_remove(source: List_T,
                           rm: List_T,
                           ) -> List_T[int]:
    n_match = -1
    indices = list()
    for i_source, item in enumerate(source):
        if item in rm:
            n_match += 1
            indices.append(i_source - n_match)
    return indices


def get_indices_to_remove(source: List_T[str],
                          idx_or_str: T_Union[int, str],
                          ) -> List_T[int]:
    if isinstance(idx_or_str, int):
        if idx_or_str < len(source):  # index within range
            indices = (idx_or_str,)
        else:
            indices = ()
            
    elif isinstance(idx_or_str, str):
        indices = find_indices_to_remove(source, (idx_or_str,))

    else:
        raise TypeError

    return indices


# --- Main ---

class ExpandoBox(QComboBox):
    def __init__(self,
                 parent=None,
                 defaults: List_T[str] = None,
                 extras: List_T[str] = None,
                 unique: bool = True,
                 n_history: int = 3,
                 n_show_extras: int = 5,
                 placeholder: str = '',
                 expander: str = '...',
                 copy: bool = True,
                 ) -> None:
        
        defaults = [] if defaults is None else defaults
        extras = [] if extras is None else extras
        self._verify_init(locals())

        super().__init__(parent)
        
        self.uniqueItemText = unique
        if copy:
            # separate internal state from external source
            defaults = deepcopy(defaults)
            extras = deepcopy(extras)
        self._defaults = defaults
        self._extras = extras
        self._history_extras: Deck_T[str] = deck([], maxlen=n_history)
        self._history_idxs: Deck_T[int] = deck([], maxlen=n_history)
        # expansion & display
        self._expander = expander
        self._is_expanded = False
        if len(self._defaults):
            # defaults only
            self.addItems(self._defaults)
            if len(self._extras):
                # defaults, expander
                self.addItem(expander)
        elif len(self._extras):
            # extras only
            self.addItems(self._extras)

        # user editing
        self.setEditable(True)
        self.setInsertPolicy(self.NoInsert)  # user cannot add item
        line_edit = self.lineEdit()
        self.line_edit = line_edit
        # completer
        self._all_items = [*self._defaults, *self._extras]
        self._allItemsStringList = QStringListModel()
        self._allItemsStringList.setStringList(self._all_items)
        completer = QCompleter()
        completer.setModel(self._allItemsStringList)
        completer.setCompletionMode(completer.PopupCompletion)
        self.setCompleter(completer)
        # display
        self.setMaxVisibleItems(len(self._defaults) + 1 + n_show_extras)
        self.setCurrentText(placeholder)
        self._previous = Previous(-1, placeholder)
        # icons
        temp = QObject()
        svg = QSvgRenderer(bytearray(clock, 'utf-8'), parent=temp)
        self.pix = QPixmap(10, 10)
        paint = QPainter(self.pix)
        svg.render(paint)
        paint.end()
        del temp
        self.clock_icon = QIcon(self.pix)
        # signal connection
        self.activated[int].connect(self.onSelect)
        line_edit.textEdited[str].connect(self.onTextEdit)
        self.completer().activated[str].connect(self.onCompleteSelect)

        # line_edit.returnPressed.connect(self.onReturnPress)  # debugging (exit a frozen widget)

    # --- Signal Handlers ---

    def onSelect(self, index: int, text: str = None) -> None:
        if text is None:
            text = self.itemText(index)

        if text == self._expander:  # expander selected
            if not self._is_expanded:
                self.toggleExtras()  # expand
            else:
                self.toggleExtras()  # collapse
            self._is_expanded = not self._is_expanded

            self.showPopup()  # keep combo list open after expansion or collapse
            # suppress selection of expander
            self.setCurrentText(self._previous.text)
            self.setCurrentIndex(self._previous.index)         
            self.setEditText('')            
        
        elif self._is_expanded:  # non-expander item selected, whilst popup is expanded
            self._previous = Previous(index, text)

            # if extra selected, update history
            if (index > len(self._defaults)):
                if self.uniqueItemText: 
                    if text not in self._history_extras:
                        self._history_extras.appendleft(text)
                elif index not in self._history_idxs:
                    self._history_extras.appendleft(text)
                    self._history_idxs.appendleft(index)

            # collapse
            self.toggleExtras()
            self.setEditText(text)

            self._is_expanded = False  # reset expansion
        else:
            self._previous = Previous(index, text)
            
    def onTextEdit(self, text: str) -> None:
        print('text edit')
        if text == '':  # blank editor
            self.showPopup()  # show all options
        else:
            super().hidePopup()  # prioritise completer popup when editing
            self.grabKeyboard()
    
    def onCompleteSelect(self, text):
        print(text)
        index = -1
        for i_item, item in enumerate(self._all_items):
            if item == text:
                index = i_item
                break
        if index >= len(self._defaults):
            index += 1
            self._is_expanded = True
        self.onSelect(index, text)

    # --- Utility ---
    
    def hidePopup(self) -> None:
        # if self._is_expanded:
        self.setCurrentText(self._previous.text)
        self.setCurrentIndex(self._previous.index)
        self.setEditText(self._previous.text)
        super().hidePopup()
    
    # def onReturnPress(self):  # debugging (exit a frozen widget)
    #     exit()
    
    def hideExtras(self):
        idx_start_extras = len(self._defaults) + 1
        hide = self._extras if self._is_expanded else self._history_extras
        for _ in hide:
            self.removeItem(idx_start_extras)

    def toggleExtras(self):
        idx_start_extras = len(self._defaults) + 1
        if self._is_expanded:
            # collapse: *defaults, expander, *extras -> *defaults, expander, *history
            for _ in self._extras:
                self.removeItem(idx_start_extras)
            for item in self._history_extras:
                self.addItem(self.clock_icon, item)
        else:
            # expand: *defaults, expander, *history -> *defaults, expander, *extras
            for _ in self._history_extras:
                self.removeItem(idx_start_extras)
            for item in self._extras:
                self.addItem(item)

    # --- Item Modification(s) ---

    def addDefault(self,
                   text: str,
                   userData: object = None,
                   ) -> None:
        if text == self._expander:
            raise err_add_expander(text)

        # update state
        n_before = len(self._defaults)
        self._defaults.append(text)
        self._all_items.insert(n_before, text)
        self.insertItem(n_before, text, userData=userData)
        self._allItemsStringList.setStringList(self._all_items)

        if (n_before == 0
        and len(self._extras)):  # first default, >=1 extra
            # show defaults: *extras -> new_default, expander
            for _ in self._extras:
                self.removeItem(1)
            self.addItem(self._expander)
    
    def addExtra(self,
                 text: str,
                 userData: object = None,
                 ) -> None:
        if text == self._expander:
            raise err_add_expander(self, text)

        # update state
        n_before = len(self._extras)
        self._extras.append(text)
        self._all_items.append(text)
        self._allItemsStringList.setStringList(self._all_items)

        if (not n_before
        and len(self._defaults)):  # first extra, >=1 default
            # show expander: *defaults -> *defaults, expander
            self.addItem(self._expander)

        elif self._is_expanded:
            # show new extra: *defaults, expander, *extras -> *defaults, expander, *extras, new_extra
            self.addItem(text, userData=userData)
    
    def addDefaults(self, texts: List_T[str]) -> None:
        if self._expander in texts:
            raise err_add_expander(self, texts)

        if len(texts):
            # update state
            n_before = len(self._defaults)
            self._defaults.extend(texts)
            self._all_items[n_before:n_before] = texts
            self.insertItems(n_before, texts)
            self._allItemsStringList.setStringList(self._all_items)

            if (not n_before
            and len(self._extras)):  # first default(s), >=1 extra
                # show default(s): *extras -> *default(s), expander, *extras
                self.insertItem(len(self._defaults), self._expander)
    
    def addExtras(self, texts: List_T[str]) -> None:
        if self._expander in texts:
            raise err_add_expander(self, texts)

        if len(texts):
            # update state
            n_before = len(self._extras)
            self._extras.extend(texts)
            self._all_items.extend(texts)
            self._allItemsStringList.setStringList(self._all_items)

            if (not n_before
            and len(self._defaults)):
                # show expander: defaults -> defaults, expander
                self.addItem(self._expander)

            elif self._is_expanded:
                # show new extras: defaults, expander, extras -> defaults, expander, extras, new_extras
                self.addItems(texts)
    
    def removeDefault(self, index_or_item: T_Union[int, str]) -> None:
        indices = get_indices_to_remove(self._defaults, index_or_item)
        for index in indices:
            # update state
            del self._defaults[index]
            del self._all_items[index]
            self.removeItem(index)
            self._allItemsStringList.setStringList(self._all_items)

            # removal
            if (not len(self._defaults)
            and len(self._extras)):  # no more defaults, >=1 extras
                # hide defaults: *defaults, expander, *extras -> *extras
                self.removeItem(0)  # remove expander
                if not self._is_expanded:
                    self._is_expanded = True
                    self.addItems(self._extras)

    def removeExtra(self, index_or_item: T_Union[int, str]) -> None:
        indices = get_indices_to_remove(self._extras, index_or_item)
        for index in indices:
            # save state
            old = self._extras[index]
            # update state
            del self._extras[index]
            n_defaults = len(self._defaults)
            del self._all_items[n_defaults + index]
            self._allItemsStringList.setStringList(self._all_items)

            # removal
            if self._is_expanded:  # popup is showing extras
                self.removeItem(n_defaults + 1 + index)
            else:
                # remove from history (if present)
                for i_hist, item in enumerate(self._history_extras):
                    if item == old:
                        self.removeItem(n_defaults + 1 + i_hist)
                        del self._history_extras[i_hist]
                        if self.uniqueItemText:
                            del self._history_idxs[i_hist]
                        break
            
            if (not len(self._extras)
            and n_defaults):  # no more extras, >=1 defaults
                # hide extras: *default(s), expander, *extras -> *defaults
                self.removeItem(n_defaults)
                self._is_expanded = False
    
    def clearDefaults(self) -> None:
        n_defaults = len(self._defaults)
        # update state
        if n_defaults:
            del self._all_items[:n_defaults]
            for _ in range(n_defaults):
                self.removeItem(0)
            if len(self._extras):
                self.removeItem(0)  # expander
        # reset state
        self._defaults = list()
    
    def clearExtras(self) -> None:
        n_extras = len(self._extras)
        # update state
        if n_extras:
            n_defaults = len(self._defaults)
            del self._all_items[n_defaults:]
            if n_defaults:
                n_rm = n_extras if self._is_expanded else len(self._history_extras)
                for _ in range(n_rm):
                    self.removeItem(n_defaults)
            else:
                self.clear()
        # reset state
        self._extras = list()
    
    def clearHistory(self) -> None:
        n_defaults = len(self._defaults)
        # update state
        if (not self._is_expanded
            and n_defaults
            and len(self._extras)):
                end_index = n_defaults + 1
                for _ in self._history_extras:
                    self.removeItem(end_index)
        # reset state                    
        self._history_extras.clear()
        self._history_idxs.clear()
    
    # --- Argument Verification ---
    def _verify_init(self, args):
        args = {key: val
                for key, val in args.items()
                if key != 'self' and key[0] != '_'}
        args = namedtuple('Args', (args.keys()))(**args)
        errors = list()
        if args.expander in set((*args.defaults, *args.extras)):
            errors.append(f"Expander character cannot be a default or extra item: '{args.expander}'")
        if args.unique:
            defaults_set = set(args.defaults)
            extras_set = set(args.extras)
            unique_errors = list()
            if len(args.defaults) > len(defaults_set):
                default_counts = Counter(args.defaults)
                repeated = [key
                            for key, count in default_counts.items()
                            if count > 1]
                unique_errors.append(f"\tThe following default items were repeated: '{repeated}'")
            if len(args.extras) > len(extras_set):
                extra_counts = Counter(args.extras)
                repeated = [key
                            for key, count in extra_counts.items()
                            if count > 1]
                unique_errors.append(f"\tThe following extra items were repeated: '{repeated}'")
            shared = defaults_set.intersection(extras_set)
            if len(shared):
                unique_errors.append(f"The following items were given as both defaults and extras: '{shared}'")
            if len(unique_errors):
                errors.append('Items were required to be unique, but one or more repeat was given.')
        if len(errors):
            raise ValueError('\n'.join(errors))


# --- Error Handling ---

def err_add_expander(self: 'ExpandoBox',
                     text_s: T_Union[str, list[str]]):
    if isinstance(text_s, str):
        return ValueError(f"Cannot add expander text as item: '{self._expander}'")

    elif isinstance(text_s, list):
        indices = {idx
                   for idx, item in enumerate(text_s)
                   if item == self._expander}
        return ValueError(f"Cannot add expander text as item: '{self._expander}'\n"
                            f"\tExpander indices: {indices}")


if __name__ == "__main__":
    import sys
    from pycuties import ExpandoBox
    from qtpy.QtWidgets import QVBoxLayout, QApplication, QWidget
    app = QApplication([])
    window = QWidget()
    window.setWindowTitle('ExpandoBox')
    layout = QVBoxLayout()
    label = QLabel(parent=window)
    label.setText('What have the Romans ever done?')
    layout.addWidget(label)
    box = ExpandoBox(defaults=['bled us dry',
                               'taken everything we had'],
                     extras=['aqueduct',
                             'sanitation',
                             'roads',
                             'irrigation',
                             'medicine',
                             'education',
                             'wine',
                             'public baths',
                             'public order',
                             'public health',
                             'fresh water system',
                             'drainage',
                             'houses',
                             'viticulture',
                             'and...',
                             'peace'],
                     n_history=2,
                     n_show_extras=15,
                     parent=window)
    layout.addWidget(box)
    window.setLayout(layout)
    window.show()
    sys.exit(app.exec())
