"""
Application Orchestrator - Manages bot sequences and workflow logic.
"""

import logging
import time
import pyautogui
import pygetwindow
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
    
    def step1_ensure_application_open(self):
        """
        Step 1: Check if the application is already open.
        Step 1.1: If not open then open it (iterate until open).
        
        Returns:
            True if application is successfully opened, False otherwise
        """
        self.logger.info("="*30)
        self.logger.info("Step 1: Checking if application is open")
        
        is_open = self.bot.is_application_open()
        if is_open:
            self.logger.info("[SUCCESS] Application is already open")
            window = self.bot.get_window_handle()
            if window:
                self.logger.info("[SUCCESS] Window handle obtained")
                return True, window
            else:
                self.logger.error("Failed to get application window handle")
                return False, None

        # Step 1.1: Iteratively try to open
        self.logger.info("Step 1.1: Application not open, attempting to open...")
        
        attempts = 0
        while attempts < self.bot.max_retries:
            attempts += 1
            self.logger.info(f"Opening attempt {attempts}/{self.bot.max_retries}")
            
            success = self.bot.open_application()
            if success:
                window = self.bot.get_window_handle()
                if window:
                    self.logger.info("[SUCCESS] Application successfully opened")
                    return True, window
                else:
                    self.logger.error("Failed to get application window handle after opening")
            
            time.sleep(1)  # Wait before retry
        
        self.logger.error("[FAILED] Failed to open application")
        return False, None
    
    def step2_maximize_application(self, window) -> bool:
        """
        Step 2: Maximize the application.
        Also ensures the application is in the foreground.
        
        Returns:
            True if successfully maximized, False otherwise
        """
        self.logger.info("="*30)
        self.logger.info("Step 2: Maximizing application")
        

        # First bring to foreground
        if not self.bot.bring_to_foreground(window):
            self.logger.warning("Could not bring to foreground, attempting to continue...")
        
        # Attempt to maximize
        if self.bot.maximize_application(window):
            self.logger.info("[SUCCESS] Maximize command sent")
            return True
        else:
            self.logger.warning("[FAILED] Initial maximize attempt failed")
            return False
    
    def step3_verify_and_fix_state(self, window) -> bool:
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
        visual_open = self.bot.check_maximized_visually()
        if not visual_open:
            attempts = 0
            while attempts < self.bot.max_retries:
                attempts += 1
                self.logger.warning("[FAILED] Visual open check failed")
                self.logger.warning("Retrying Step 2.")
                self.step2_maximize_application(window)
        else:
            self.logger.info("[SUCCESS] Visual open check passed")
        
        # Step 3.2: Check maximized state
        self.logger.info("Step 3.2: Checking maximized state")
        if window and self.bot.check_maximized_visually():
            self.logger.info("[SUCCESS] Application is properly maximized")
            return True
        
        # Step 3.3: Iteratively maximize if needed
        self.logger.info("Step 3.3: Application not maximized, attempting iterative maximization")
        
        attempts = 0
        while attempts < self.bot.max_retries:
            attempts += 1
            self.logger.info(f"Maximization attempt {attempts}/{self.bot.max_retries}")
            
            # Ensure foreground first
            if window:
                self.bot.maximize_application(window)
                time.sleep(1)
                
                # Check if successful
                if self.bot.check_maximized_visually():
                    self.logger.info("[SUCCESS] Successfully maximized")
                    return True
            else:
                self.logger.error("No window reference available for maximization")
            
        self.logger.error("[FAILED] Failed to properly maximize application")
        return False
    
    def run_startup_sequence(self) -> bool:
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
        process_found, window = self.step1_ensure_application_open()
        if not process_found or window is None:
            return False
        
        # Execute Step 2
        if not self.step2_maximize_application(window):
            self.logger.warning("Step 2 had issues, continuing to verification...")
        
        # Execute Step 3
        if not self.step3_verify_and_fix_state(window):
            self.logger.error("Sequence failed at Step 3")
            return False
        
        # Final verification
        self.logger.info("="*30)
        self.logger.info("Final verification...")
        
        # Ensure still in foreground
        if window and not self.bot.is_foreground(window):
            self.logger.info("Bringing back to foreground...")
            self.bot.bring_to_foreground(window)
        
        elapsed_time = time.time() - start_time
        
        self.logger.info("="*50)
        self.logger.info("[SUCCESS] APPLICATION MANAGEMENT SEQUENCE COMPLETED")
        self.logger.info(f"[SUCCESS] Total time: {elapsed_time:.2f} seconds")
        self.logger.info("[SUCCESS] Application is: OPEN | FOREGROUND | MAXIMIZED")
        self.logger.info("="*50)
        
        return True
    
    def get_status_report(self) -> Dict[str, Any]:
        """
        Get a status report of the current application state.
        
        Returns:
            Dictionary containing current status information
        """
        is_open = self.bot.is_application_open()
        window = self.bot.get_window_handle() if is_open else None
        status = {
            'process_running': is_open,
            'window_exists': window is not None,
            'is_foreground': self.bot.is_foreground(window) if window else False,
            'is_maximized': self.bot.check_maximized_visually() if window else False
        }
        
        return status