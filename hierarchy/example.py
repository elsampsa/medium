"""An example Qt code for a composite widget with:

- A list with an active element
- A form
- Buttons for CRUD actions
- List, buttons and form interact with the state of the model

Please read the associated medium article to understand what this is all about.

Before running this file, remember to install:

::

    pip3 install --user PySide2

We want to demonstrate here the hierarchical organization and restriction of communication
between the GUI objects, the "View" and the "Model".

We're _not_ using here the full-blown View/Model system offered by Qt as it would obscure our
purposes to simply demonstrate some ideas.

Here's the object hierarchy as discussed in the medium article:

::

    WListForm:
        STATE:
            uuid   # current active record
            cache  # a dummy "database"

        WList
            IN:
                set_data(datums: list)
                set_uuid(uuid: str)
            UP:
                signals.uuid (str)

        WForm
            STATE:
                current active record (editable)
                visibility state of record fields
            IN: 
                set_data(datum: Datum)
                set_visible(viz: bool)
            UP: 
                get_data() -> dict
        
        WButtons
            STATE:
                visibility state of buttons "save", "delete"
            IN: 
                set_visible(viz: bool)
            UP: 
                signals.new
                signals.save
                signals.delete

Some additional things you might learn/want to use:

- Standard practice: SomeClass is in camel case while an instatiated object some_class is in kebab case
- Using namespaces to organize members / internal objects
- A context manager for Qt signal blocking
- Setters do not emit signals
- Using sensible names for methods, so that code becomes "evident"/easy to read
"""
from PySide2.QtWidgets import *                                                                                                
from PySide2.QtCore import *                                                                                                   
from PySide2.Qt import *
from uuid import uuid1


class Namespace:

    def __init__(self):
        pass


class Datum:

    def __init__(self, name, surname, uuid):
        self.name = name
        self.surname = surname
        self.uuid = uuid


class NoSignals:
    """A context manager for blocking Qt signals
    """
    def __init__(self, widget):
        self.widget = widget
        self.blocker = QSignalBlocker(widget)
        self.blocker.unblock()

    def __enter__(self):
        self.blocker.reblock()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_type is None:
            self.blocker.unblock()
        else:
            print("NoSignals exception", exc_type)


class WButtons(QWidget):
    """Group of buttons: new, save, delete

    ::

        IN: 
            set_visible(viz: bool)

        UP: 
            signals.new
            signals.save
            signals.delete
    
    """
    def __init__(self, parent = None):
        super().__init__(parent)
        self.lay = QHBoxLayout(self)
        self.new_button = QPushButton("New", self)
        self.save_button = QPushButton("Save", self)
        self.delete_button = QPushButton("Delete", self)
        # we _could_ organize buttons under namespace self.buttons.
        self.lay.addWidget(self.new_button)
        self.lay.addWidget(self.save_button)
        self.lay.addWidget(self.delete_button)
        # aliases:
        self.signals = Namespace()
        self.signals.new = self.new_button.clicked
        self.signals.save = self.save_button.clicked
        self.signals.delete = self.delete_button.clicked


    def set_visible(self, viz: bool):
        """IN

        Set the visibility of self.save_button and self.delete_button
        """
        self.save_button.setVisible(viz)
        self.delete_button.setVisible(viz)


class WList(QWidget):
    """List of database elements
    
    ::

        IN: 
            set_data(datums: list)
            set_uuid(uuid: str)
        UP: 
            signals.uuid (str)
    
    """
    class Signals(QObject):
        uuid = Signal(object)


    def __init__(self, parent = None):
        super().__init__(parent)
        self.signals = self.Signals()
        self.lay = QVBoxLayout(self)
        self.q_list_widget = QListWidget(self)
        self.lay.addWidget(self.q_list_widget)
        # set internal connections
        self.q_list_widget.currentItemChanged.connect(
            self.__set_uuid_item_slot
        )

    def __set_uuid_item_slot(self, q_list_widget_item_new, q_list_widget_item_old):
        """internal: connect here a signal with the uuid of the current item
        """
        print("WList: __set_uuid_item_slot")
        if q_list_widget_item_new is None:
            print("WList: __set_uuid_item_slot: None")
            self.signals.uuid.emit(None) # nothing chosen yet
        else:
            self.signals.uuid.emit(q_list_widget_item_new.uuid) # send uuid of the chosen element
    
    def set_data(self, datums: list):
        """IN

        :param datums: a list of Datum objects

        NOTE: no signals emitted
        """
        with NoSignals(self.q_list_widget):
            self.q_list_widget.clear() # this result in calling __set_uuid_item_slot
            self.items = []
            for datum in datums:
                # CustomDataElement members: name, uuid
                item = QListWidgetItem(
                    datum.name + " " + datum.surname
                )
                # attach an extra member to QListWidgetItem.
                # this is a hack you can only do in python Qt
                item.uuid = datum.uuid
                self.q_list_widget.addItem(item)
                self.items.append(item) # an aux list
                print("WList: set_data:",datum.name, datum.surname, datum.uuid)
            
    def set_uuid(self, uuid: str):
        """IN

        NOTE: no signals emitted
        """
        with NoSignals(self.q_list_widget):
            print("WList: set_uuid",uuid)
            for item in self.items:
                print("WList:",item.uuid, uuid)
                if item.uuid == uuid:
                    self.q_list_widget.setCurrentItem(item)
                    return
            self.q_list_widget.setCurrentItem(None)


class WForm(QWidget):
    """Input form

    ::

        STATE:
            current active record (editable)
        IN: 
            set_data(datum: Datum)
        UP: 
            get_data() -> dict

    """
    def __init__(self, parent):
        super().__init__(parent)
        # this should be a work for a code generator instead of automagic classes
        self.lay = QGridLayout(self)
        # name        
        self.label_name = QLabel("Name", self)
        self.field_name = QLineEdit(self)
        self.lay.addWidget(self.label_name, 0, 1)
        self.lay.addWidget(self.field_name, 0, 2)
        # surname
        self.label_surname = QLabel("Surname", self)
        self.field_surname = QLineEdit(self)
        self.lay.addWidget(self.label_surname, 1, 1)
        self.lay.addWidget(self.field_surname, 1, 2)


    def get_data(self) -> dict:
        """UP
        """
        return {
            "name"      : self.field_name.text(),
            "surname"   : self.field_surname.text()
        }

    def set_data(self, datum: Datum):
        """IN
        """
        self.field_name.setText(datum.name)
        self.field_surname.setText(datum.surname)


    def set_visible(self, viz: bool):
        """IN

        Set the visibility of the whole widget
        """
        self.setVisible(viz)


class WListForm(QWidget):
    """Master/top level object managing other widgets and the model    
    """
    def __init__(self, parent = None):
        super().__init__(parent)

        self.lay = QHBoxLayout(self)
        self.left = QWidget(self)
        self.right = QWidget(self)
        self.lay.addWidget(self.left)
        self.lay.addWidget(self.right)
        
        self.left_lay = QVBoxLayout(self.left)
        self.right_lay = QVBoxLayout(self.right)

        self.w_list_1 =\
            WList(self.left)
        self.left_lay.addWidget(self.w_list_1)

        self.w_form_1 =\
            WForm(self.right)
        self.right_lay.addWidget(self.w_form_1)

        self.w_buttons_1 =\
            WButtons(self.right)
        self.right_lay.addWidget(self.w_buttons_1)

        # connect signals from child objects
        # from WList
        self.w_list_1.signals.uuid.connect(
            self.recv_wlist_uuid
        )
        # from WButtons
        self.w_buttons_1.signals.new.connect(
            self.recv_wbuttons_new
        )
        self.w_buttons_1.signals.save.connect(
            self.recv_wbuttons_save
        )
        self.w_buttons_1.signals.delete.connect(
            self.recv_wbuttons_delete
        )
        
        self.state = Namespace()
        """The only state that matters is cached here, in the top-level object to these variables:
        self.state.cache      # key: uuid, value: Datum object
        self.state.uuid       # the uuid of the currently chosen object
        """
        self.initDB() # self.state.cache defined here
        self.w_list_1.set_data([datum for datum in self.state.cache.values()])
        self.state.uuid = list(self.state.cache.keys())[0]
        self.w_list_1.set_uuid(self.state.uuid)
        self.w_form_1.set_data(self.state.cache[self.state.uuid])


    def initDB(self):
        uid1 = uuid1()
        uid2 = uuid1()
        self.state.cache = {
            uid1: Datum("Mickey", "Mouse", uid1),
            uid2: Datum("Walt", "Disney", uid2)
        }

    # signals receivers from children

    def recv_wlist_uuid(self, uuid):
        """From WList
        """
        self.state.uuid = uuid
        if uuid is None:
            return # None chosen
        print("WListForm: recv_wlist_uuid: current active element",self.state.cache[uuid])
        self.w_form_1.set_data(self.state.cache[uuid])


    def recv_wbuttons_new(self):
        """From WButtons
        """
        self.w_form_1.set_visible(True)
        self.w_buttons_1.set_visible(True)
        uuid = uuid1()
        print("WListForm: recv_wbuttons_new: uuid:", uuid)
        self.state.cache[uuid] = Datum("<nada>","<nada>",uuid)
        self.state.uuid = uuid
        self.w_list_1.set_data([datum for datum in self.state.cache.values()])
        self.w_list_1.set_uuid(self.state.uuid)
        self.w_form_1.set_visible(True)
        self.w_form_1.set_data(self.state.cache[uuid])


    def recv_wbuttons_save(self):
        """From WButtons
        """
        record = self.w_form_1.get_data()
        print("WListForm: recv_wbuttons_save")
        self.state.cache[self.state.uuid] = Datum(
            record["name"], 
            record["surname"], 
            self.state.uuid)
        self.w_list_1.set_data([datum for datum in self.state.cache.values()])
        self.w_list_1.set_uuid(self.state.uuid)


    def recv_wbuttons_delete(self):
        """From WButtons
        """
        print("WListForm: recv_wbuttons_delete")
        self.state.cache.pop(self.state.uuid)
        self.w_list_1.set_data([datum for datum in self.state.cache.values()])
        if len(self.state.cache) < 1:
            self.state.uuid = None
            self.w_form_1.set_visible(False)
            self.w_buttons_1.set_visible(False)
        else:
            self.state.uuid = list(self.state.cache.keys())[0]
            self.w_form_1.set_data(self.state.cache[self.state.uuid])
        self.w_list_1.set_uuid(self.state.uuid)
        

def main():
    app=QApplication(["test_app"])
    mg=WListForm()
    mg.show()
    app.exec_()

    
if __name__ == "__main__":
    main()

