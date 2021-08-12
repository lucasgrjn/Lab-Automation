from typing import Type, Optional, List, Union, Generator
import yaml
from yaml.representer import Representer
from abc import ABCMeta

from commands.command import Command
from devices.device import Device
from commands.utility_commands import LoopStartCommand, LoopEndCommand


# Representer.add_representer(ABCMeta, Representer.represent_name)

# Should move loop interpretation to invoker?
# Make functional with yaml safe_load

class CommandSequence:
    """Maintains a command list with optional iterations and looping. Supports saving/loading."""
    recipe_directory = 'recipes/'

    def __init__(self):
        self.device_list = []
        self.command_list = []
        self.num_iterations = 'ALL'
        # self.processed_devices = []
        # self.processed_commands = []
        # self.processed_delays = []
        self.device_by_name = {}

    def add_device(self, receiver: Device):
        """Add a device to the device list then update the device dict.

        Parameters
        ----------
        receiver : Device
            The device to add.
        """
        self.device_list.append(receiver)
        self.update_device_by_name()

    def remove_device(self, receiver_name: str):
        """Remove a device from the device list then update the device dict.

        Parameters
        ----------
        receiver_name : str
            The name attribute of the device/receiver to remove.
        """
        if receiver_name in self.device_by_name:
            for ndx, device in enumerate(self.device_list):
                if device.name == receiver_name:
                    del self.device_list[ndx]
                    self.update_device_by_name()
                    break # Each device should have a unique name, always

    def remove_device_by_index(self, index: Optional[int] = None):
        """Remove a device from the device list by index then update the device dict.

        Parameters
        ----------
        index : Optional[int], optional
            The index of the device to remove, If index is None remove the last device, by default None
        """
        if index is None:
            index = -1
        del self.device_list[index]
        self.update_device_by_name()

    def add_command(self, command: Union[Command, List[Command]], index: Optional[int] = None):
        """Add a command to the command list.

        Parameters
        ----------
        command : Union[Command, List[Command]]
            A command or a list of commands to add at the index, If a list is passed then the list corresponds to multiple iterations of the command at the index.
        index : Optional[int], optional
            The index to insert the command, If None then appends the command, by default None
        """
        if not isinstance(command, list):
            command = [command]
        if index is None:
            self.command_list.append(command)
        else:
            self.command_list.insert(index, command)
    
    def remove_command(self, index: Optional[int] = None):
        """Remove a command from the command list.

        Parameters
        ----------
        index : Optional[int], optional
            The index of the command to remove, If None the remove the last command, by default None
        """
        if index is None:
            index = -1
        del self.command_list[index]

    def move_command_by_index(self, old_index: int, new_index: int):
        """Move the command or command iterations to a different index in the command list.

        Parameters
        ----------
        old_index : int
            The index of the command(s) to move
        new_index : int
            The index to move the command(s) to
        """
        if old_index >= 0 and old_index <= len(self.command_list) - 1 and new_index >= 0 and new_index <= len(self.command_list) - 1:
            if old_index != new_index:
                self.command_list.insert(new_index, self.command_list.pop(old_index))
        else:
            print("Invalid indices")

    def add_loop_start(self, index: Optional[int] = None):
        """Add a LoopStartCommand to the command list.

        Parameters
        ----------
        index : Optional[int], optional
            The index to insert the command, If None then append the command, by default None
        """
        self.add_command(LoopStartCommand(), index)

    def add_loop_end(self, index: Optional[int] = None):
        """Add a LoopEndCommand to the command list.

        Parameters
        ----------
        index : Optional[int], optional
            The index to insert the command, If None then append the command, by default None
        """
        self.add_command(LoopEndCommand(), index)

    def add_command_iteration(self, command: Union[Command, List[Command]], index: Optional[int] = None, iteration: Optional[int] = None):
        """Add command(s) as iterations to a pre-existing command in the command list.

        Parameters
        ----------
        command : Union[Command, List[Command]]
            The command or list of commands to add as iterations
        index : Optional[int], optional
            The index of the pre-existing command to add iterations to, If None then adds to the last command, by default None
        iteration : Optional[int], optional
            The iteration index to add the command(s) at, by default None
        """
        if not isinstance(command, list):
            command = [command]
        if index is None:
            index = -1
        if iteration is None:
            # add to end of iteration list
            self.command_list[index].extend(command)
        else:
            # insert at specific iteration index
            for ndx in range(len(command)):
                self.command_list[index].insert(iteration, command.pop(-1))

    def remove_command_iteration(self, index: Optional[int] = None, iteration: Optional[int] = None):
        """Remove a command iteration from a command's iteration list.

        Parameters
        ----------
        index : Optional[int], optional
            The index of the command to remove an iteration from, if None then removes from the last command, by default None
        iteration : Optional[int], optional
            The iteration index of the command iteration to remove, if None then removes the last iteration, by default None
        """
        if index is None:
            index = -1
        if iteration is None:
            iteration = -1
        del self.command_list[index][iteration]

    def move_command_iteration_by_index(self, index: int, old_iter: int, new_iter: int):
        """Move a command iteration to a different index in the command's iteration list.

        Parameters
        ----------
        index : int
            The index of the command to move around one if it's iterations
        old_iter : int
            The iteration index of the iteration to move
        new_iter : int
            The new iteration index to move the iteration to
        """
        if old_iter >= 0 and old_iter <= len(self.command_list[index]) - 1 and new_iter >= 0 and new_iter <= len(self.command_list[index]) - 1:
            if old_iter != new_iter:
                self.command_list[index].insert(new_iter, self.command_list[index].pop(old_iter))
        else:
            print("Invalid indices")

    def verify_device_list(self):
        # each device must be unique (by name attribute)
        pass

    def verify_command_list(self):
        # loop end must be after loop start
        # either they are both included or both not included
        # iteration list has commands of same class
        pass
    
    def update_device_by_name(self):
        """Update the device dict that stores each device/receiver by it's name."""

        self.device_by_name = {}
        for device in self.device_list:
            self.device_by_name[device.name] = device

    def get_unlooped_command_list(self) -> List[Command]:
        """Get the full unlooped command list by pre-evaluating any loops.

        Returns
        -------
        List[Command]
            The unlooped command list
        """
        unlooped_list= []
        command_generator = self.yield_next_command()
        for command in command_generator:
            unlooped_list.append(command)
        return unlooped_list      

    def yield_next_command(self) -> Generator[Command, None, None]:
        """A generator that yields each command sequentially, accounting for loops.

        Yields
        -------
        Generator[Command, None, None]
            Generator that yields the next command
        """
        # originally used this function to pre-process the whole unlooped list
        # changed to generator that yields next command
        # if the whole unlooped list is wanted then get_unlooped_command_list use this function to populate a list
        # generator is likely unnecessary but have both methods here for flexibility

        #perform verify here !!!!!!!
        # unlooped_list = []
        index = 0
        iteration = 0
        loop_start_index = None
        if self.num_iterations == 'ALL':
            max_iterations = self.get_max_iteration()
        else:
            max_iterations = self.num_iterations

        while index < len(self.command_list):
            # Get the command at the current index and iteration
            # if current iteration is larger than the number of the current command's iterations then use the last one
            if iteration > len(self.command_list[index]) - 1:
                command = self.command_list[index][-1]
            else:
                command = self.command_list[index][iteration]
            
            if isinstance(command, LoopStartCommand):
                loop_start_index = index
                index += 1
                continue

            if isinstance(command, LoopEndCommand):
                iteration += 1
                if iteration < max_iterations:
                    index = loop_start_index + 1
                    continue
                else:
                    iteration = 0
                    index += 1
                    continue

            # unlooped_list.append([command])
            yield command
            index += 1
        # return unlooped_list

    def get_max_iteration(self) -> int:
        """Gets the length of the largest command iteration list.

        Returns
        -------
        int
            The largest iteration length
        """
        max_iter = 1
        for command in self.command_list:
            if len(command) > max_iter:
                max_iter = len(command)
        return max_iter

    def save_to_yaml(self, filename: str):
        """Save the device_list, command_list, and num_iterations to a .yaml file.

        Parameters
        ----------
        filename : str
            The filename of the .yaml to save to
        """
        filename = self.recipe_directory + filename
        data_list = [self.device_list, self.command_list, self.num_iterations]
        with open(filename, 'w') as file:
            yaml.dump(data_list, file, default_flow_style=False, sort_keys=False)

    def load_from_yaml(self, filename: str):
        """Load the device_list, command_list, and num_iterations from a .yaml file.

        Parameters
        ----------
        filename : str
            The filename of the .yaml to load from
        """
        filename = self.recipe_directory + filename
        with open(filename) as file:
            # not safe loader
            imported_list = yaml.load(file, Loader=yaml.Loader)
            self.device_list = imported_list[0]
            self.command_list = imported_list[1]
            self.num_iterations = imported_list[2]

    def get_command_names(self, unloop: bool = False) -> List[str]:
        """Get a list of command names, either with a loop or unlooped.

        Parameters
        ----------
        unloop : bool, optional
            Whether to have the list unlooped or not, by default False

        Returns
        -------
        List[str]
            The list of command names 
        """
        name_list = []
        if unloop:
            for command in self.yield_next_command():
                name_list.append(command.name)
        else:
            for command in self.command_list:
                for iter_ndx, iter_command in enumerate(command):
                    if iter_ndx == 0:
                        name_list.append(iter_command.name)
                    else:
                        name_list.append("    Iter#" + str(iter_ndx + 1) + ": " + iter_command.name)
        return name_list

    def get_command_names_descriptions(self, unloop: bool = False) -> List[List[str]]:
        """Get a list of [command names, command descriptions] either with a loop or unlooped.

        Parameters
        ----------
        unloop : bool, optional
            Whether to have the list unlooped or not, by default False

        Returns
        -------
        List[List[str]]
            The list of [command names, command descriptions] 
        """
        name_desc_list = []
        if unloop:
            for command in self.yield_next_command():
                name_desc_list.append(["Name: " + command.name, "Description: " + command.description])
        else:
            for command in self.command_list:
                for iter_ndx, iter_command in enumerate(command):
                    if iter_ndx == 0:
                        name_desc_list.append(["Name: " + iter_command.name, "Description: " + iter_command.description])
                    else:
                        name_desc_list.append(["    Iter#" + str(iter_ndx + 1) + ": " + "Name: " + iter_command.name,
                                                 "    Iter#" + str(iter_ndx + 1) + ": " + "Description: " + iter_command.description])
        return name_desc_list

    def print_command_names(self):
        """Print the command names with any loop."""
        for name in self.get_command_names(unloop=False):
            print(name)
    
    def print_unlooped_command_names(self):
        """Print the command names unlooped."""
        for name in self.get_command_names(unloop=True):
            print(name)

    def print_command_names_descriptions(self):
        """Print the command names and descriptions with any loop."""
        for name_desc in self.get_command_names_descriptions(unloop=False):
            print(name_desc[0])
            print(name_desc[1])

    def print_unlooped_command_names_descriptions(self):
        """Print the command names and descriptions unlooped."""
        for name_desc in self.get_command_names_descriptions(unloop=True):
            print(name_desc[0])
            print(name_desc[1])