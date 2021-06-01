"""

NOTE:
    - to emulate combobox popup and selection:
            xbox.showPopup()
            xbox.onSelect(*)
            xbox.hidePopup()
        - couldn't find which object to pass to pytestqt.qtbot

TODO:
    - docstrings
    - GUI testing
        - window and/or keyboard focus
        - selection
        - user editing
            - completion
            - robustness
    - basic API testing
        - adding item(s)
        - removing item(s)
        - clearing defaults|extras|history
    - edge-case API testing
        - adding first default/extra
        - removing last default/extra
        - removing out-of-bounds index/indices
        - removing extra(s) that has been added to history
"""

# stdlib
import random
from inspect import signature
from collections import deque as deck
# pypi
from qtpy.QtWidgets import QApplication
from PyQt5 import sip
# local
from pycuties.expandobox import ExpandoBox

# testing
import pytest
from hypothesis import (given, assume,
                        strategies as st,)
# type hinting
from typing import (Union as T_Union,
                    Optional as Optional_T,
                    Tuple as Tuple_T,
                    List as List_T,)


# --- Utility ---

default_expander = signature(ExpandoBox.__init__).parameters['expander'].default

# pytest
depends = pytest.mark.depends
skip = pytest.mark.skip

# hypothesis
SearchStrategy = st.SearchStrategy
string = st.text()
string_not_expander = string.filter(lambda s: s != default_expander)
boolean = st.booleans()

varied_nums = (0, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1_000)
small_nums = (0, 1, 2, 5, 10, 20)


def integer_sample(small=False, nonzero=False):
    options = small_nums if small \
         else varied_nums
    options = options[nonzero:]
    return st.sampled_from(options)


# type hinting
Integer_T = T_Union[int, SearchStrategy[int]]
Boolean_T = T_Union[bool, SearchStrategy[bool]]
String_T = T_Union[str, SearchStrategy[str]]
Items_T = T_Union[List_T[str], None]
GetItems_T = Tuple_T[bool, List_T[int], List_T[int]]
GetInitItems_T = Tuple_T[bool, Optional_T[List_T[int]], Optional_T[List_T[int]]]


@st.composite
def get_items(draw, content: String_T = string,
                    min_len: Integer_T = 1,
                    max_len: Integer_T = integer_sample(),
                    unique: Boolean_T = boolean,
                    expander: String_T = default_expander,
                    ) -> GetItems_T:
    """[summary]

    Args:
        draw ([type]): [description]
        content (String_T, optional): [description]. Defaults to string_not_expander.
        min_len (int[0:], optional): [description]. Defaults to 0.
        max_len (Integer_T, optional): [description]. Defaults to integer_sample().
        nonzero (bool, optional): [description]. Defaults to True.
        unique (Boolean_T, optional): [description]. Defaults to boolean.

    Raises:
        ValueError: [description]

    Returns:
        GetItems_T: [description]
    """
    if isinstance(min_len, SearchStrategy):
        min_len = draw(min_len)
    max_strat = None
    if isinstance(max_len, SearchStrategy):
        max_strat = max_len
        max_len = draw(max_len.filter(lambda n: n >= min_len))

    if min_len < 0 or max_len < 0:
        raise ValueError
    assume(max_len >= min_len)
    
    if isinstance(unique, SearchStrategy):
        unique = draw(unique)
    

    if not unique:
        if isinstance(expander, SearchStrategy):
            expander = draw(expander)
        content = content.filter(lambda s: s != expander)
        items = st.lists(content, min_size=min_len,
                                  max_size=max_len)
        defaults = draw(items)
        extras = draw(items)

    else:
        n_defaults = max_len
        if max_strat is None:
            n_extras = random.randint(min_len, max_len)
        else:
            n_extras = draw(max_strat.filter(lambda n: n >= min_len))
        # n_extras = draw(max_len)
        # assume(n_min <= n_extras)
        n_items = n_defaults + n_extras

        items = set()
        for _ in range(n_items):  # + bool(min_len)):
            # item = draw(content.filter(lambda s: s not in items))
            item = draw(content)
            assume(item not in items)
            items.add(item)
        items = list(items)
        defaults = items[:n_defaults]
        extras = items[n_defaults:]
    
    return (unique, defaults, extras)

@st.composite
def get_init_items(draw):
    unique__defaults__extras = draw(get_items(min_len=0,
                                              expander=string))
    unique, defaults, extras = unique__defaults__extras
    
    none_defaults = draw(boolean)
    none_extras = draw(boolean)
    if none_defaults:
        defaults = None
    if none_extras:
        extras = None

    return unique, defaults, extras


# PyQt
app = QApplication([])


# --- Main ---

@given(expander = string,
       placeholder = string,
       uniq__defaults__extras = get_init_items())
@depends(name='init')
def test_init(expander: str,
              placeholder: str,
              uniq__defaults__extras: GetInitItems_T,
              ):
    """

    Args:
        defaults (Items_T): 
        extras (Items_T): 
        expander (str): 
        placeholder (str): 
    
    Cases:

    ╭──────────────────────────┬───────────────────────────┬───────────────────────────┬───────────────────────────╮
    │                          │                           │                           │                           │
    │    ╭─────────────┬───╮   │    ╭─────────────┬───╮    │    ╭─────────────┬───╮    │    ╭─────────────┬───╮    │
    │    │ placeholder │ ▽ │   │    │ placeholder │ ▽ │    │    │ placeholder │ ▽ │    │    │ placeholder │ ▽ │    │
    │    ├─────────────┴───┤   │    ├─────────────┴───┤    │    ├─────────────┴───┤    │    ├─────────────┴───┤    │
    │    ╰ ─ ─ ─ ─ ─ ─ ─ ─ ┘   │    ¦ default         ¦    │    ¦ extra           ¦    │    ¦ default         ¦    │
    │                          │    ¦   :             ¦    │    ¦   :             ¦    │    ¦   :             ¦    │
    │                          │    ╰ ─ ─ ─ ─ ─ ─ ─ ─ ┘    │    ╰ ─ ─ ─ ─ ─ ─ ─ ─ ┘    │    ¦ expander        ¦    │
    │                          │                           │                           │    ╰ ─ ─ ─ ─ ─ ─ ─ ─ ┘    │
    │                          │                           │                           │                           │
    ╰──────────────────────────┴───────────────────────────┴───────────────────────────┴───────────────────────────┘

    """
    # --- Prep ---
    unique, defaults, extras = uniq__defaults__extras
    kwargs = {'defaults': defaults,
              'extras': extras,
              'expander': expander,
              'placeholder': placeholder,
              'unique': unique}
    defaults = [] if defaults is None else defaults
    extras = [] if extras is None else extras
    
    # --- Act ---
    if expander in set((*defaults, *extras)):
        try:
            xbox = ExpandoBox(**kwargs)
        except ValueError:
            return
    else:
        xbox = ExpandoBox(**kwargs)

    # --- Check ---
    # attributes
    assert xbox._defaults == defaults
    assert xbox._extras == extras
    assert xbox._all_items == [*defaults, *extras]
    # placeholder value
    assert xbox.lineEdit().text() == placeholder
    # item count
    both = len(defaults) and len(extras)
    if both:
        assert xbox.count() == len(defaults) + 1
    else:
        assert xbox.count() == len(defaults) + len(extras)
    # item values
    items = [*defaults, expander] if both \
    else [*defaults, *extras]
    for i_item, item in enumerate(items):
        assert xbox.itemText(i_item) == item

    # --- End ---
    sip.delete(xbox)


@depends(on=['init'], name='dropdown')
class TestDropdown:
    def test_basic(_, ):
        ...

    
    def test_robust(_, ):
        ...
    

@depends(on=['init'])
class TestSelectPreExpansion:
    def test_defaults_only(_, ):
        """[summary]

        Args:
            _ ([type]): [description]
        
        ╭──────────────────────────────────────────────────╮
        │                                                  │
        │    ╭──────────┬───╮          ╭──────────┬───╮    │
        │    │ previous │ ▼ │    ->    │ default  │ ▽ │    │
        │    ├──────────┴───┤          ╰──────────┴───┘    │
        │  ▶ │ default      │                              │
        │    │   :          │                              │
        │    ╰──────────────┘                              │
        │                                                  │
        ╰──────────────────────────────────────────────────┘
        """
        ...
    
    def test_extras_only(_, ):
        """[summary]

        Args:
            _ ([type]): [description]
        
        ╭──────────────────────────────────────────────────╮
        │                                                  │
        │    ╭──────────┬───╮          ╭──────────┬───╮    │
        │    │ previous │ ▼ │    ->    │ extra    │ ▽ │    │
        │    ├──────────┴───┤          ╰──────────┴───┘    │
        │  ▶ │ extra        │                              │
        │    │   :          │                              │
        │    ╰──────────────┘                              │
        │                                                  │
        ╰──────────────────────────────────────────────────┘
        """
        ...
    
    def test_default_w_expander(_, ):
        """[summary]

        Args:
            _ ([type]): [description]
        
        ╭──────────────────────────────────────────────────╮
        │                                                  │
        │    ╭──────────┬───╮          ╭──────────┬───╮    │
        │    │ previous │ ▼ │    ->    │ default  │ ▽ │    │
        │    ├──────────┴───┤          ╰──────────┴───┘    │
        │  ▶ │ default      │                              │
        │    │   :          │                              │
        │    │ expander     │                              │
        │    ╰──────────────┘                              │
        │                                                  │
        ╰──────────────────────────────────────────────────┘
        """
        ...


# @depends(on=['init', 'dropdown'], name='expand-collapse')
class TestExpandCollapse:
    # @depends(name='expand')
    class TestExpand:
        @given(placeholder=string,
               uniq__defaults__extras = get_items())
        def test_from_init(_, placeholder: str,
                              uniq__defaults__extras: GetItems_T,
                              ):
            """
            ╭─────────────────────────────────────────────────────╮
            │                                                     │
            │    ╭─────────────┬───╮          ╭──────────┬───╮    │
            │    │ placeholder │ ▼ │    ->    │ |        │ ▼ │    │
            │    ├─────────────┴───┤          ├──────────┴───┤    │
            │    │ default         │          │ default      │    │
            │    │   :             │          │   :          │    │
            │  ▶ │ expander        │          │ expander     │    │
            │    ╰─────────────────┘          │ extra        │    │
            │                                 │   :          │    │
            │                                 ╰──────────────┘    │
            │                                                     │
            ╰─────────────────────────────────────────────────────┘

            """
            # --- Prep ---
            unique, defaults, extras = uniq__defaults__extras
            xbox = ExpandoBox(defaults=defaults,
                              extras=extras,
                              placeholder=placeholder,
                              unique=unique)
            idx_expander = len(defaults)

            # --- Act ---
            xbox.showPopup()
            xbox.onSelect(idx_expander)

            # --- Check ---
            for i_item, item in enumerate((*defaults, default_expander, *extras)):
                assert xbox.itemText(i_item) == item
            assert xbox.lineEdit().text() == ''

            # --- End ---
            sip.delete(xbox)
        
        @given(uniq__defaults__extras = get_items())
        def test_from_previous(_, uniq__defaults__extras: GetItems_T):
            """
            ╭──────────────────────────────────────────────────╮
            │                                                  │
            │    ╭──────────┬───╮          ╭──────────┬───╮    │
            │    │ previous │ ▼ │    ->    │ |        │ ▼ │    │
            │    ├──────────┴───┤          ├──────────┴───┤    │
            │    │ default      │          │ default      │    │
            │    │   :          │          │   :          │    │
            │  ▶ │ expander     │          │ expander     │    │
            │    ╰──────────────┘          │ extra        │    │
            │                              │   :          │    │
            │                              ╰──────────────┘    │
            │                                                  │
            ╰──────────────────────────────────────────────────┘

            """
            # --- Prep ---
            unique, defaults, extras = uniq__defaults__extras
            xbox = ExpandoBox(defaults=defaults,
                              extras=extras,
                              unique=unique)
            idx_expander = len(defaults)
            idx_previous = random.randint(0, idx_expander - 1)
            previous = defaults[idx_previous]
            xbox.showPopup()
            xbox.onSelect(idx_previous)
            xbox.hidePopup()

            # --- Check ---
            for i_item, item in enumerate((*defaults, default_expander)):
                assert xbox.itemText(i_item) == item
            assert xbox.itemText(xbox.currentIndex()) == previous
            assert xbox.lineEdit().text() == previous
            
            # --- Act ---
            xbox.showPopup()
            xbox.onSelect(idx_expander)

            # --- Check ---
            for i_item, item in enumerate((*defaults, default_expander, *extras)):
                assert xbox.itemText(i_item) == item
            assert xbox.lineEdit().text() == ''
            assert xbox.itemText(xbox.currentIndex()) == previous

            # --- End ---
            sip.delete(xbox)
    
    # @depends(on=['expand'])
    class TestCollapse:
        @given(placeholder = string,
               uniq__defaults__extras = get_items())
        def test_from_init(_, placeholder: str,
                              uniq__defaults__extras: GetItems_T,
                              ):
            """
            ╭───────────────────────────────────────────────────────────────────────────────╮
            │                                                                               │
            │    ╭─────────────┬───╮          ╭──────────┬───╮          ╭──────────┬───╮    │
            │    │ placeholder │ ▼ │    ->    │ |        │ ▼ │    ->    │ |        │ ▼ │    │
            │    ├─────────────┴───┤          ├──────────┴───┤          ├──────────┴───┤    │
            │    │ default         │          │ default      │          │ default      │    │
            │    │   :             │          │   :          │          │   :          │    │
            │  ▶ │ expander        │        ▶ │ expander     │          │ expander     │    │
            │    ╰─────────────────┘          │ extra        │          ╰──────────────┘    │
            │                                 │   :          │                              │
            │                                 ╰──────────────┘                              │
            │                                                                               │
            ╰───────────────────────────────────────────────────────────────────────────────┘

            """
            # --- Prep ---
            unique, defaults, extras = uniq__defaults__extras
            xbox = ExpandoBox(defaults=defaults,
                              extras=extras,
                              placeholder=placeholder,
                              unique=unique)
            idx_expander = len(defaults)

            # --- Act ---
            xbox.showPopup()
            xbox.onSelect(idx_expander)

            # --- Check ---
            for i_item, item in enumerate((*defaults, default_expander, *extras)):
                assert xbox.itemText(i_item) == item
            assert xbox.lineEdit().text() == ''
            
            # --- Act ---
            xbox.onSelect(idx_expander)
            xbox.hidePopup()

            # --- Check ---
            for i_item, item in enumerate((*defaults, default_expander)):
                assert xbox.itemText(i_item) == item
            assert xbox.lineEdit().text() == placeholder

            # --- End ---
            sip.delete(xbox)
        
        @given(uniq__defaults__extras = get_items())
        def test_from_previous(_, uniq__defaults__extras: GetItems_T):
            """
            ╭────────────────────────────────────────────────────────────────────────────╮
            │                                                                            │
            │    ╭──────────┬───╮          ╭──────────┬───╮          ╭──────────┬───╮    │
            │    │ previous │ ▼ │    ->    │ |        │ ▼ │    ->    │ previous │ ▼ │    │
            │    ├──────────┴───┤          ├──────────┴───┤          ├──────────┴───┤    │
            │    │ default      │          │ default      │          │ default      │    │
            │    │   :          │          │   :          │          │   :          │    │
            │  ▶ │ expander     │        ▶ │ expander     │          │ expander     │    │
            │    ╰──────────────┘          │ extra        │          ╰──────────────┘    │
            │                              │   :          │                              │
            │                              ╰──────────────┘                              │
            │                                                                            │
            ╰────────────────────────────────────────────────────────────────────────────┘

            """
            # --- Prep ---
            unique, defaults, extras = uniq__defaults__extras
            xbox = ExpandoBox(defaults=defaults,
                              extras=extras,
                              unique=unique)
            idx_expander = len(defaults)
            idx_previous = random.randint(0, idx_expander - 1)
            previous = defaults[idx_previous]
            xbox.showPopup()
            xbox.onSelect(idx_previous)
            xbox.hidePopup()

            # --- Check ---
            for i_item, item in enumerate((*defaults, default_expander)):
                assert xbox.itemText(i_item) == item
            assert xbox.itemText(xbox.currentIndex()) == previous
            assert xbox.lineEdit().text() == previous
            
            # --- Act ---
            xbox.showPopup()
            xbox.onSelect(idx_expander)

            # --- Check ---
            for i_item, item in enumerate((*defaults, default_expander, *extras)):
                assert xbox.itemText(i_item) == item
            assert xbox.lineEdit().text() == ''
            assert xbox.itemText(xbox.currentIndex()) == previous

            # --- Act ---
            xbox.onSelect(idx_expander)
            xbox.hidePopup()

            # --- Check ---
            for i_item, item in enumerate((*defaults, default_expander)):
                assert xbox.itemText(i_item) == item
            assert xbox.itemText(xbox.currentIndex()) == previous
            assert xbox.lineEdit().text() == previous

            # --- End ---
            sip.delete(xbox)


@depends(['expand-collapse'])
class TestSelectPostExpansion:
    def test_default(_, ):
        """[summary]

        Args:
            _ ([type]): [description]
        
        ╭──────────────────────────────────────────────────╮
        │                                                  │
        │    ╭──────────┬───╮          ╭──────────┬───╮    │
        │    │ |        │ ▼ │    ->    │ default  │ ▽ │    │
        │    ├──────────┴───┤          ╰──────────┴───┘    │
        │  ▶ │ default      │                              │
        │    │   :          │                              │
        │    │ expander     │                              │
        │    │ extra        │                              │
        │    │   :          │                              │
        │    ╰──────────────┘                              │
        │                                                  │
        ╰──────────────────────────────────────────────────┘
        """
        ...
    
    def test_extra(_, ):
        """[summary]

        Args:
            _ ([type]): [description]
        
        ╭──────────────────────────────────────────────────╮
        │                                                  │
        │    ╭──────────┬───╮          ╭──────────┬───╮    │
        │    │ |        │ ▼ │    ->    │ extra    │ ▽ │    │
        │    ├──────────┴───┤          ╰──────────┴───┘    │
        │    │ default      │                              │
        │    │   :          │                              │
        │    │ expander     │                              │
        │  ▶ │ extra        │                              │
        │    │   :          │                              │
        │    ╰──────────────┘                              │
        │                                                  │
        ╰──────────────────────────────────────────────────┘
        """
        ...


# @depends(on=['init', 'expand-collapse'])
class TestHistory:
    @given(n_history=integer_sample(small=True),
           uniq__defaults__extras = get_items())
    def test_first_extra(_, n_history: int,
                            uniq__defaults__extras: GetItems_T,
                            ):
        ...
        """
        ╭──────────────────────────────────────────────────────────────────────────────────────────────────────╮
        │                                                                                                      │
        │    ╭──────────┬───╮          ╭──────────┬───╮          ╭──────────┬───╮          ╭──────────┬───╮    │
        │    │ previous │ ▼ │    ->    │ previous │ ▼ │    ->    │ extra    │ ▽ │    ->    │ extra    │ ▼ │    │
        │    ├──────────┴───┤          ├──────────┴───┤          ╰──────────────┘          ├──────────┴───┤    │
        │    │ default      │          │ default      │                                    │ default      │    │
        │    │   :          │          │   :          │                                    │   :          │    │
        │  ▶ │ expander     │          │ expander     │                                    │ expander     │    │
        │    ╰──────────────┘        ▶ │ extra        │                                    │ @ extra      │    │
        │                              │   :          │                                    ╰──────────────┘    │
        │                              ╰──────────────┘                                                        │
        │                                                                                                      │
        ╰──────────────────────────────────────────────────────────────────────────────────────────────────────┘

        """
        # --- Prep ---
        unique, defaults, extras = uniq__defaults__extras
        xbox = ExpandoBox(defaults=defaults,
                          extras=extras,
                          n_history=n_history,
                          unique=unique)
        idx_expander = len(defaults)
        idx_extra = random.randint(0, len(extras) - 1)
        historic_extra = extras[idx_extra]
        # expand
        # xbox.showPopup()
        xbox.onSelect(idx_expander)

        # --- Act ---
        xbox.onSelect(idx_expander + 1 + idx_extra)
        # xbox.hidePopup()
        # xbox.showPopup()

        # --- Check ---
        expected_items = [*defaults, default_expander]
        if n_history > 0:
            expected_items.append(historic_extra)
        expected_items += [''] * 10

        for i_item, item in enumerate(expected_items):
            assert xbox.itemText(i_item) == item

        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        # TODO
        #   - how to actually fetch item icon?
        #       neither itemIcon, itemData(n, QtCore.Qt.DecorationRole) work)
        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
        # print(f'{xbox.clock_icon=}')
        # for i_item in range(n_defaults + 1):
        #     print(f'{i_item=} {xbox.itemIcon(i_item)=}')
        #     print(f'{i_item=} {xbox.itemData(i_item, Qt.DecorationRole)=}')
        #     # assert xbox.itemIcon(i_item) is None
        # for i_item, _ in enumerate(extras, start=n_defaults + 1):
        #     print(f'{i_item=} {xbox.itemIcon(i_item)=}')
        #     print(f'{i_item=} {xbox.itemData(i_item, Qt.DecorationRole)=}')
        #     # assert xbox.itemIcon(i_item) is xbox.clock_icon
        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

        # --- End ---
        xbox.hidePopup()
        sip.delete(xbox)
    
    @given(n_history = integer_sample(nonzero=True),
           uniq__defaults__extras = get_items(unique=True))
    def test_wo_replacement(_, uniq__defaults__extras: GetItems_T,
                               n_history: int,
                               ):
        """

        Args:
            _ ([type]): 
            uniq__defaults__extras (GetItems_T): 
            n_history (int): 

        Cases:

        ╭──────────────────────────────────────────────────────────────────────────────────────────────────────────╮
        │   n_history = 1       n_extra >= n_history                                                               │
        ├──────────────────────────────────────────────────────────────────────────────────────────────────────────┤
        │                                                                                                          │
        │    ╭───────────┬───╮          ╭───────────┬───╮          ╭───────────┬───╮          ╭───────────┬───╮    │
        │    │ previous  │ ▼ │    ->    │ |         │ ▼ │    ->    │ n+1_extra │ ▽ │    ->    │ n+1_extra │ ▼ │    │
        │    ├───────────┴───┤          ├───────────┴───┤          ╰───────────┴───┘          ├───────────┴───┤    │
        │    │ default       │          │ default       │                                     │ default       │    │
        │    │   :           │          │   :           │                                     │   :           │    │
        │  ▶ │ expander      │          │ expander      │                                     │ expander      │    │
        │    │ @ nth_extra   │          │ extra         │                                     │ @ n+1_extra   │    │
        │    ╰───────────────┘          │   :           │                                     ╰───────────────┘    │
        │      n >= n_history         ▶ │ n+1_extra     │                                                          │
        │                               │   :           │                                                          │
        │                               ╰───────────────┘                                                          │
        │                                                                                                          │
        ╰──────────────────────────────────────────────────────────────────────────────────────────────────────────┘

        ╭──────────────────────────────────────────────────────────────────────────────────────────────────────────╮
        │   n_history > 1       n_extra >= n_history                                                               │
        ├──────────────────────────────────────────────────────────────────────────────────────────────────────────┤
        │                                                                                                          │
        │                                                                                       n_history > 2      │
        │    ╭───────────┬───╮          ╭───────────┬───╮          ╭───────────┬───╮          ╭───────────┬───╮    │
        │    │ previous  │ ▼ │    ->    │ |         │ ▼ │    ->    │ n+1_extra │ ▽ │    ->    │ n+1_extra │ ▼ │    │
        │    ├───────────┴───┤          ├───────────┴───┤          ╰───────────┴───┘          ├───────────┴───┤    │
        │    │ default       │          │ default       │                 |                   │ default       │    │
        │    │   :           │          │   :           │                 V                   │   :           │    │
        │  ▶ │ expander      │          │ expander      │            n_history = 2            │ expander      │    │
        │    │ @ nth_extra   │          │ extra         │          ╭───────────┬───╮          │ @ n+1_extra   │    │
        │    │   :           │          │   :           │          │ n+1_extra │ ▼ │          │ @ nth_extra   │    │
        │    │ @ mth_extra   │        ▶ │ n+1_extra     │          ├───────────┴───┤          │   :           │    │
        │    ╰───────────────┘          │   :           │          │ default       │          │ @ m+1_extra   │    │
        │        0 < m < n              ╰───────────────┘          │   :           │          ╰───────────────┘    │
        │      n >= n_history                                      │ expander      │                               │
        │                                                          │ @ n+1_extra   │                               │
        │                                                          │ @ nth_extra   │                               │
        │     mth_extra != nth_extra != n+1_extra != m+1_extra     ╰───────────────┘                               │
        │                                                                                                          │
        ╰──────────────────────────────────────────────────────────────────────────────────────────────────────────┘

        """
        # --- Prep ---
        unique, defaults, extras = uniq__defaults__extras
        xbox = ExpandoBox(defaults=defaults,
                          extras=extras,
                          n_history=n_history,
                          unique=unique)
        idx_expander = len(defaults)
        n_extras = len(extras)
        n_sample = min(n_history, n_extras)
        idxs_extras = random.sample(range(n_extras), k=n_sample)
        history = deck(maxlen=n_history)

        # --- Act ---
        for _ in range(n_sample):
            # test state
            idx_save = idxs_extras.pop(-1)
            history.appendleft(extras[idx_save])
            # actions
            # xbox.showPopup()
            xbox.onSelect(idx_expander)
            xbox.onSelect(idx_expander + 1 + idx_save)
            # xbox.hidePopup()
        # xbox.showPopup()
        
        # --- Check ---
        expected_items = [*defaults, default_expander, *history] + [''] * 10
        for i_item, item in enumerate(expected_items):
            assert xbox.itemText(i_item) == item

        # --- End ---
        # xbox.hidePopup()
        sip.delete(xbox)

    @given(n_history=integer_sample(small=True, nonzero=True),
           uniq__defaults__extras = get_items())
    def test_w_replacement(_, n_history: int,
                              uniq__defaults__extras: GetItems_T,
                              ):
        """[summary]

        Args:
            _ ([type]): [description]



        ╭──────────────────────────────────────────────────────────────────────────────────────────────────────────╮
        │                                                                                                          │
        │                                                                                     x not in {i ... k}   │
        │    ╭───────────┬───╮          ╭───────────┬───╮          ╭───────────┬───╮          ╭───────────┬───╮    │
        │    │ previous  │ ▼ │    ->    │ |         │ ▼ │    ->    │ extra_x   │ ▽ │    ->    │ n+1_extra │ ▼ │    │
        │    ├───────────┴───┤          ├───────────┴───┤          ╰───────────┴───┘          ├───────────┴───┤    │
        │    │ default       │          │ default       │                 |                   │ default       │    │
        │    │   :           │          │   :           │                 V                   │   :           │    │
        │  ▶ │ expander      │          │ expander      │           x in {i ... k}            │ expander      │    │
        │    │ @ extra_i     │          │ extra         │          ╭───────────┬───╮          │ @ extra_x     │    │
        │    │   :           │          │   :           │          │ n+1_extra │ ▼ │          │ @ extra_i     │    │
        │    │ @ extra_k     │        ▶ │ extra_x       │          ├───────────┴───┤          │   :           │    │
        │    ╰───────────────┘          │   :           │          │ default       │          │ @ extra_j     │    │
        │                               ╰───────────────┘          │   :           │          ╰───────────────┘    │
        │                                                          │ expander      │                               │
        │                                                          │ @ extra_i     │                               │
        │                                                          │   :           │                               │
        │                                                          │ @ extra_k     │                               │
        │                                                          ╰───────────────┘                               │
        │                                                                                                          │
        ╰──────────────────────────────────────────────────────────────────────────────────────────────────────────┘


        """
        # --- Prep ---
        unique, defaults, extras = uniq__defaults__extras
        xbox = ExpandoBox(defaults=defaults,
                          extras=extras,
                          n_history=n_history,
                          unique=unique)
        idx_expander = len(defaults)
        n_extras = len(extras)
        n_sample = 2 * n_extras
        idxs_extras = random.choices(range(n_extras), k=n_sample)
        history_text = deck(maxlen=n_history)
        history_idxs = deck(maxlen=n_history)

        # --- Act ---
        for _ in range(n_sample):
            # test state
            idx_select = idxs_extras.pop(-1)
            if idx_select not in history_idxs:
                history_idxs.appendleft(idx_select)
                history_text.appendleft(extras[idx_select])
            # action
            # xbox.showPopup()
            xbox.onSelect(idx_expander)
            xbox.onSelect(idx_expander + 1 + idx_select)
            # xbox.hidePopup()
        # xbox.showPopup()
        
        # --- Check ---
        expected_items = [*defaults, default_expander, *history_text] + [''] * 10
        for i_item, item in enumerate(expected_items):
            assert xbox.itemText(i_item) == item

        # --- End ---
        # xbox.hidePopup()
        sip.delete(xbox)


class TestSelectPostHistory:
    def test_default(_, ):
        """[summary]

        Args:
            _ ([type]): [description]
        
        ╭──────────────────────────────────────────────────╮
        │                                                  │
        │    ╭──────────┬───╮          ╭──────────┬───╮    │
        │    │ previous │ ▼ │    ->    │ default  │ ▽ │    │
        │    ├──────────┴───┤          ╰──────────┴───┘    │
        │  ▶ │ default      │                              │
        │    │   :          │                              │
        │    │ expander     │                              │
        │    │ @ historic   │                              │
        │    │   :          │                              │
        │    ╰──────────────┘                              │
        │                                                  │
        ╰──────────────────────────────────────────────────┘
        """
        ...
    
    def test_historic_extra(_, ):
        """[summary]

        Args:
            _ ([type]): [description]
        
        ╭──────────────────────────────────────────────────╮
        │                                                  │
        │    ╭──────────┬───╮          ╭──────────┬───╮    │
        │    │ previous │ ▼ │    ->    │ historic │ ▽ │    │
        │    ├──────────┴───┤          ╰──────────┴───┘    │
        │    │ default      │                              │
        │    │   :          │                              │
        │    │ expander     │                              │
        │  ▶ │ @ historic   │                              │
        │    │   :          │                              │
        │    ╰──────────────┘                              │
        │                                                  │
        ╰──────────────────────────────────────────────────┘
        """
        ...

    def test_regular_extra(_, ):
        """[summary]

        Args:
            _ ([type]): [description]
        
        ╭────────────────────────────────────────────────────────────────────────────╮
        │                                                                            │
        │    ╭──────────┬───╮          ╭──────────┬───╮          ╭──────────┬───╮    │
        │    │ previous │ ▼ │    ->    │ extra    │ ▼ │    ->    │ extra    │ ▽ │    │
        │    ├──────────┴───┤          ├──────────┴───┤          ╰──────────┴───┘    │
        │    │ default      │          │ default      │                              │
        │    │   :          │          │   :          │                              │
        │  ▶ │ expander     │          │ expander     │                              │
        │    │ @ historic   │        ▶ │ extra        │                              │
        │    │   :          │          │   :          │                              │
        │    ╰──────────────┘          ╰──────────────┘                              │
        │                                                                            │
        ╰────────────────────────────────────────────────────────────────────────────┘
        """
        ...


# @depends(on=['init'])
class TestCompleter:
    @skip  # TODO
    @given(uniq__defaults__extras = get_items(min_len=0))
    def test_suggestions(_, uniq__defaults__extras: GetItems_T):
        # nothing, defaults only, extras only, both
        # --- Prep ---

        # --- Act ---

        # --- Check ---

        # --- End ---

        pass


    

    @skip  # TODO
    @given(uniq__defaults__extras = get_items())
    def test_select_suggestion(_, uniq__defaults__extras: GetItems_T):
        """

        Args:
            defaults (Items_T): 
            extras (Items_T): 
        
        Cases:

        
        
        """
        # --- Prep ---
        

        # --- Act ---

        # --- Check ---

        # --- End ---

        pass




# @depends(on=['init'])
class TestAddItem_s:
    @given(new_default = string,
           clicked = boolean,
           uniq__defaults__extras = get_init_items())
    def test_add_default(_, new_default: str,
                            clicked: bool,
                            uniq__defaults__extras: GetInitItems_T,
                         ):
        """

        Args:
            defaults (Items_T): 
            extras (Items_T): 
            new_default (str): 
            clicked (bool): 

        Cases:

        ╭────────────────────────────────────────────────┬────────────────────────────────────────────────╮
        │                                                │                                                │
        │    ╭─────────┬───╮    +     ╭─────────┬───╮    │    ╭─────────┬───╮    +     ╭─────────┬───╮    │
        │    │         │▼/▽│    ->    │         │▼/▽│    │    │         │▼/▽│    ->    │         │▼/▽│    │
        │    ├─────────┴───┤          ├─────────┴───┤    │    ├─────────┴───┤          ├─────────┴───┤    │
        │    ╰─────────────┘          │ new_default │    │    │ default     │          │ default     │    │
        │                             ╰─────────────┘    │    │   :         │          │   :         │    │
        │                                                │    ╰─────────────┘          │ new_default │    │
        │                                                │                             ╰─────────────┘    │
        │                                                │                                                │
        ├────────────────────────────────────────────────┼────────────────────────────────────────────────┤
        │                                                │                                                │
        │    ╭─────────┬───╮    +     ╭─────────┬───╮    │    ╭─────────┬───╮    +     ╭─────────┬───╮    │
        │    │         │▼/▽│    ->    │         │▼/▽│    │    │         │▼/▽│    ->    │         │▼/▽│    │
        │    ├─────────┴───┤          ├─────────┴───┤    │    ├─────────┴───┤          ├─────────┴───┤    │
        │    │ extra       │          │ new_default │    │    │ default     │          │ default     │    │
        │    │   :         │          │ expander    │    │    │   :         │          │  :          │    │
        │    ╰─────────────┘          │ new_default │    │    │ expander    │          │ new_default │    │
        │                             ╰─────────────┘    │    ╰─────────────┘          │ expander    │    │
        │                                                │                             ╰─────────────┘    │
        │                                                │                                                │
        ├────────────────────────────────────────────────┼────────────────────────────────────────────────┴────────────────────────╮
        │                                                │                                                                         │
        │    ╭─────────┬───╮    +     ╭─────────┬───╮    │    ╭─────────┬───╮          ╭─────────┬───╮    +     ╭─────────┬───╮    │
        │    │         │▼/▽│    ->    │         │▼/▽│    │    │ |       │ ▼ │    ->    │ |       │ ▼ │    ->    │ |       │ ▼ │    │
        │    ├─────────┴───┤          ├─────────┴───┤    │    ├─────────┴───┤          ├─────────┴───┤          ├─────────┴───┤    │
        │    │ default     │          │ default     │    │    │ default     │          │ default     │          │ default     │    │
        │    │   :         │          │   :         │    │    │   :         │          │   :         │          │   :         │    │
        │    │ expander    │          │ new_default │    │  ▶ │ expander    │          │ expander    │          │ new_default │    │
        │    │ @ historic  │          │ expander    │    │    ╰─────────────┘          │ extra       │          │ expander    │    │
        │    │   :         │          │ @ historic  │    │                             │   :         │          │ extra       │    │
        │    ╰─────────────┘          │   :         │    │                             ╰─────────────┘          │   :         │    │
        │                             ╰─────────────┘    │                                                      ╰─────────────┘    │
        │                                                │                                                                         │
        ╰────────────────────────────────────────────────┴─────────────────────────────────────────────────────────────────────────┘

        """
        # --- Prep ---
        # __init__
        unique, defaults, extras = uniq__defaults__extras
        xbox = ExpandoBox(defaults=defaults,
                          extras=extras,
                          unique=unique)
        defaults = [] if defaults is None else defaults
        extras = [] if extras is None else extras
        # possible selection
        expanded = False
        if clicked:
            index = random.randint(0, max(0, xbox.count() - 1))
            xbox.onSelect(index)
            # possible expansion
            expanded = (xbox.itemText(index) == default_expander)
        # expected items
        if len(extras):
            items = [*defaults, new_default, default_expander]
            if expanded:
                items.extend(extras)
        else:
            items = [*defaults, new_default]

        # --- Act ---
        if new_default == default_expander:
            try:
                xbox.addDefault(new_default)
            except ValueError:
                return
        else:
            xbox.addDefault(new_default)
        
        # --- Check ---
        for i_item, item in enumerate(items):
            assert xbox.itemText(i_item) == item
        
        # --- End ---
        sip.delete(xbox)

    @skip  # TODO
    @given()
    def test_add_extra(_, ):
        """
        ╭────────────────────────────────────────────────┬────────────────────────────────────────────────╮
        │                                                │                                                │
        │    ╭─────────┬───╮    +     ╭─────────┬───╮    │    ╭─────────┬───╮    +     ╭─────────┬───╮    │
        │    │         │▼/▽│    ->    │         │▼/▽│    │    │         │▼/▽│    ->    │         │▼/▽│    │
        │    ├─────────┴───┤          ├─────────┴───┤    │    ├─────────┴───┤          ├─────────┴───┤    │
        │    ╰─────────────┘          │ new_extra   │    │    │ extra       │          │ extra       │    │
        │                             ╰─────────────┘    │    │   :         │          │   :         │    │
        │                                                │    ╰─────────────┘          │ new_extra   │    │
        │                                                │                             ╰─────────────┘    │
        │                                                │                                                │
        ├────────────────────────────────────────────────┼────────────────────────────────────────────────┤
        │                                                │                                                │
        │    ╭─────────┬───╮    +     ╭─────────┬───╮    │    ╭─────────┬───╮    +     ╭─────────┬───╮    │
        │    │         │▼/▽│    ->    │         │▼/▽│    │    │         │▼/▽│    ->    │         │▼/▽│    │
        │    ├─────────┴───┤          ├─────────┴───┤    │    ├─────────┴───┤          ├─────────┴───┤    │
        │    │ default     │          │ default     │    │    │ default     │          │ default     │    │
        │    │   :         │          │   :         │    │    │   :         │          │  :          │    │
        │    ╰─────────────┘          │ expander    │    │    │ expander    │          │ expander    │    │
        │                             ╰─────────────┘    │    ╰─────────────┘          ╰─────────────┘    │
        │                                                │                                                │
        │                                                │                                                │
        │                                                │                                                │
        ├────────────────────────────────────────────────┼────────────────────────────────────────────────┴────────────────────────╮
        │                                                │                                                                         │
        │    ╭─────────┬───╮    +     ╭─────────┬───╮    │    ╭─────────┬───╮          ╭─────────┬───╮    +     ╭─────────┬───╮    │
        │    │         │▼/▽│    ->    │         │▼/▽│    │    │ |       │ ▼ │    ->    │ |       │ ▼ │    ->    │ |       │ ▼ │    │
        │    ├─────────┴───┤          ├─────────┴───┤    │    ├─────────┴───┤          ├─────────┴───┤          ├─────────┴───┤    │
        │    │ default     │          │ default     │    │    │ default     │          │ default     │          │ default     │    │
        │    │   :         │          │   :         │    │    │   :         │          │   :         │          │   :         │    │
        │    │ expander    │          │ expander    │    │  ▶ │ expander    │          │ expander    │          │ expander    │    │
        │    │ @ historic  │          │ @ historic  │    │    ╰─────────────┘          │ extra       │          │ extra       │    │
        │    │   :         │          │   :         │    │                             │   :         │          │   :         │    │
        │    ╰─────────────┘          ╰─────────────┘    │                             ╰─────────────┘          │ new_extra   │    │
        │                                                │                                                      ╰─────────────┘    │
        │                                                │                                                                         │
        ╰────────────────────────────────────────────────┴─────────────────────────────────────────────────────────────────────────┘
        """
        # --- Prep ---

        # --- Act ---

        # --- Check ---

        # --- End ---

        pass

    @skip  # TODO
    @given()
    def test_add_defaults(_, ):
        # --- Prep ---

        # --- Act ---

        # --- Check ---

        # --- End ---
        
        pass

    @skip  # TODO
    @given()
    def test_add_extras(_, ):
        # --- Prep ---

        # --- Act ---

        # --- Check ---

        # --- End ---
        
        pass


class TestRemoveItem_s:
    @skip  # TODO
    @given()
    def test_remove_default(_, ):
        # --- Prep ---

        # --- Act ---

        # --- Check ---

        # --- End ---
        
        pass

    @skip  # TODO
    @given()
    def test_remove_extra(_, ):
        # --- Prep ---

        # --- Act ---

        # --- Check ---

        # --- End ---
        
        pass

    @skip  # TODO
    @given()
    def test_clear_defaults(_, ):
        # --- Prep ---

        # --- Act ---

        # --- Check ---

        # --- End ---
        
        pass

    @skip  # TODO
    @given()
    def test_clear_extras(_, ):
        # --- Prep ---

        # --- Act ---

        # --- Check ---

        # --- End ---
        
        pass

    @skip  # TODO
    @given()
    def test_clear_history(_, ):
        # --- Prep ---

        # --- Act ---

        # --- Check ---

        # --- End ---
        
        pass
