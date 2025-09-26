"""
Application Orchestrator - Manages bot sequences and workflow logic.
"""

import logging
import time
import pyautogui
from typing import Dict, Any, TYPE_CHECKING

# Import type for type hints without circular dependency
if TYPE_CHECKING:
    from bot.application_bot import ApplicationManagerBot


class ApplicationOrchestrator:
    """
    Orchestrator that manages the bot and executes the complete sequence of actions.
    Handles the flow logic and step verification separately from bot operations.
    """
    
    def __init__(self, bot: 'ApplicationManagerBot'):
        """
        Initialize the orchestrator with a bot instance.
        
        Args:
            bot: An instance of ApplicationManagerBot to control
        """
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.logger.info("Orchestrator initialized")
    
    def step1_ensure_application_open(self) -> bool:
        """
        Step 1: Check if the application is already open.
        Step 1.1: If not open then open it (iterate until open).
        
        Returns:
            True if application is successfully opened, False otherwise
        """
        self.logger.info("="*30)
        self.logger.info("Step 1: Checking if application is open")
        
        if self.bot.is_application_open():
            self.logger.info("✓ Application is already open")
            return True
        
        # Step 1.1: Iteratively try to open
        self.logger.info("Step 1.1: Application not open, attempting to open...")
        
        attempts = 0
        while attempts < self.bot.max_retries:
            attempts += 1
            self.logger.info(f"Opening attempt {attempts}/{self.bot.max_retries}")
            
            if self.bot.open_application():
                # Wait and check if it opened
                time.sleep(2)
                if self.bot.is_application_open():
                    self.logger.info("✓ Application successfully opened")
                    return True
            
            time.sleep(2)  # Wait before retry
        
        self.logger.error("✗ Failed to open application")
        return False
    
    def step2_maximize_application(self) -> bool:
        """
        Step 2: Maximize the application.
        Also ensures the application is in the foreground.
        
        Returns:
            True if successfully maximized, False otherwise
        """
        self.logger.info("="*30)
        self.logger.info("Step 2: Maximizing application")
        
        # First bring to foreground
        if not self.bot.bring_to_foreground():
            self.logger.warning("Could not bring to foreground, attempting to continue...")
        
        # Attempt to maximize
        if self.bot.maximize_application():
            self.logger.info("✓ Maximize command sent")
            return True
        else:
            self.logger.warning("✗ Initial maximize attempt failed")
            return False
    
    def step3_verify_and_fix_state(self) -> bool:
        """
        Step 3: Check if the application is open and maximised.
        Step 3.1: Use icon/image template to check visually if the application is open.
        Step 3.2: Check for positions of the icons/templates to check visually that the application is maximised.
        Step 3.3: If not maximised, iteratively try to maximise it and check if it is maximised.
        
        Returns:
            True if application is verified open and maximized, False otherwise
        """
        self.logger.info("="*30)
        self.logger.info("Step 3: Verifying application state")
        
        # Step 3.1: Visual check for open state
        self.logger.info("Step 3.1: Visual verification of open state")
        visual_open = self.bot.check_visual_open()
        if not visual_open:
            self.logger.warning("✗ Visual open check failed")
            # Try refreshing window handle
            self.bot.refresh_window_handle()
        else:
            self.logger.info("✓ Visual open check passed")
        
        # Step 3.2: Check maximized state
        self.logger.info("Step 3.2: Checking maximized state")
        if self.bot.check_maximized_visually():
            self.logger.info("✓ Application is properly maximized")
            return True
        
        # Step 3.3: Iteratively maximize if needed
        self.logger.info("Step 3.3: Application not maximized, attempting iterative maximization")
        
        attempts = 0
        while attempts < self.bot.max_retries:
            attempts += 1
            self.logger.info(f"Maximization attempt {attempts}/{self.bot.max_retries}")
            
            # Ensure foreground first
            self.bot.bring_to_foreground()
            
            # Try maximize
            self.bot.maximize_application()
            time.sleep(1)
            
            # Check if successful
            if self.bot.check_maximized_visually():
                self.logger.info("✓ Successfully maximized")
                return True
            
            # Try alternative method with keyboard
            if attempts == 2:
                self.logger.info("Trying keyboard shortcut method")
                self.bot.bring_to_foreground()
                time.sleep(0.5)
                pyautogui.hotkey('win', 'up')
                time.sleep(1)
                
                if self.bot.check_maximized_visually():
                    self.logger.info("✓ Keyboard method successful")
                    return True
        
        self.logger.error("✗ Failed to properly maximize application")
        return False
    
    def run_complete_sequence(self) -> bool:
        """
        Execute the complete sequence following all specified steps.
        
        Returns:
            True if all steps completed successfully, False otherwise
        """
        self.logger.info("="*50)
        self.logger.info("STARTING APPLICATION MANAGEMENT SEQUENCE")
        self.logger.info("="*50)
        
        start_time = time.time()
        
        # Execute Step 1
        if not self.step1_ensure_application_open():
            self.logger.error("Sequence failed at Step 1")
            return False
        
        # Execute Step 2
        if not self.step2_maximize_application():
            self.logger.warning("Step 2 had issues, continuing to verification...")
        
        # Execute Step 3
        if not self.step3_verify_and_fix_state():
            self.logger.error("Sequence failed at Step 3")
            return False
        
        # Final verification
        self.logger.info("="*30)
        self.logger.info("Final verification...")
        
        # Ensure still in foreground
        if not self.bot.is_foreground():
            self.logger.info("Bringing back to foreground...")
            self.bot.bring_to_foreground()
        
        elapsed_time = time.time() - start_time
        
        self.logger.info("="*50)
        self.logger.info("✓ APPLICATION MANAGEMENT SEQUENCE COMPLETED")
        self.logger.info(f"✓ Total time: {elapsed_time:.2f} seconds")
        self.logger.info("✓ Application is: OPEN | FOREGROUND | MAXIMIZED")
        self.logger.info("="*50)
        
        return True
    
    def get_status_report(self) -> Dict[str, Any]:
        """
        Get a status report of the current application state.
        
        Returns:
            Dictionary containing current status information
        """
        status = {
            'process_running': self.bot.is_application_open(),
            'window_exists': self.bot.window is not None,
            'is_foreground': self.bot.is_foreground() if self.bot.window else False,
            'is_maximized': self.bot.check_maximized_visually() if self.bot.window else False,
            'visual_check': self.bot.check_visual_open() if self.bot.icon_template is not None else None
        }
        
        return status