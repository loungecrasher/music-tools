"""
Tests for the common Menu system.
"""

import pytest
from unittest.mock import Mock, patch
from music_tools_common.ui.menu import Menu, MenuOption

class TestMenu:
    """Test Menu class functionality."""
    
    def test_initialization(self):
        """Test menu initialization."""
        menu = Menu("Test Menu")
        assert menu.title == "Test Menu"
        assert len(menu.options) == 0
        assert menu.exit_option is None
        
    def test_add_option(self):
        """Test adding options."""
        menu = Menu("Test")
        action = Mock()
        
        menu.add_option("Option 1", action, "Description")
        
        assert len(menu.options) == 1
        assert menu.options[0].name == "Option 1"
        assert menu.options[0].action == action
        assert menu.options[0].description == "Description"
        
    def test_set_exit_option(self):
        """Test setting exit option."""
        menu = Menu("Test")
        action = Mock()
        
        menu.set_exit_option("Exit", action)
        
        assert menu.exit_option is not None
        assert menu.exit_option.name == "Exit"
        assert menu.exit_option.action == action
        
    def test_create_submenu(self):
        """Test submenu creation."""
        menu = Menu("Main")
        submenu = menu.create_submenu("Sub")
        
        assert isinstance(submenu, Menu)
        assert submenu.title == "Sub"
        assert submenu.parent_menu == menu
        
        # Check that submenu option was added to main menu
        assert len(menu.options) == 1
        assert menu.options[0].name == "Sub"
