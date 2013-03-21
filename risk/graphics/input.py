###############################################################################
## Input is handled by state transition diagram where mouse clicks will trigger
## state changes.
#

import time

import pygame

import risk
import risk.logger
import risk.graphics.assets.player

from risk import graphics
from risk.errors.input import UserQuitInput
from risk.errors.game_master import GameMasterError
from risk.errors.battle import RiskBattleError

from risk.graphics.datastore import Datastore
from risk.graphics.picasso import get_picasso
from risk.graphics.assets.player import *
from risk.graphics.assets.territory import TerritoryAsset
from risk.graphics.assets.dialog import BlockingNumericDialogAsset

LAYER = '5_player_feedback'
INPUT_POLL_SLEEP = 0.1
MAX_INPUT_LENGTH = 3

def get_clicked_territories(mouse_pos):
    return graphics.pressed_clickables(mouse_pos, 'territories')

def get_clicked_buttons(mouse_pos):
    return graphics.pressed_clickables(mouse_pos, 'buttons')

def handle_user_mouse_input(game_master, state_entry):
    player = game_master.current_player()
    state_entry(player, game_master)
    #scan_pygame_mouse_event(player, game_master, state_entry)
    
def scan_pygame_mouse_event():
    _WAITING_FOR_INPUT = True
    while _WAITING_FOR_INPUT:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise UserQuitInput()
            elif event.type == pygame.MOUSEBUTTONUP:
                return event
        time.sleep(INPUT_POLL_SLEEP)

def wait_for_territory_click():
    _NO_TERRITORY_CLICKED = True
    while _NO_TERRITORY_CLICKED:
        event = scan_pygame_mouse_event()
        for name, clickable in get_clicked_territories(event.pos):
            if isinstance(clickable, TerritoryAsset):
                return clickable

###############################################################################
## Reinforce phase DFA
#

def reinforce_phase(player, game_master):
    # state init vector
    datastore = Datastore()
    picasso = get_picasso()
    reserve_count_asset = ReserveCountAsset(player)
    picasso.add_asset(LAYER, reserve_count_asset)
    # core state machine
    while player.reserves > 0:
        event = scan_pygame_mouse_event()
        for name, clickable in graphics.pressed_clickables(event.pos, 
                'territories'):
            if isinstance(clickable, TerritoryAsset):
                territory = clickable.territory
                # makegonow for now, fix later
                try:
                    reinforce_add_army(player, game_master, territory)
                except GameMasterError:
                    reinforce_add_army_fail(player, game_master, territory)
    # exit state
    picasso.remove_asset(LAYER, reserve_count_asset)

def reinforce_add_army(player, game_master, territory, number_of_armies=1):
    game_master.player_add_army(player, territory.name, number_of_armies)

def reinforce_add_army_fail(player, game_master, territory):
    risk.logger.debug("%s does not own %s" % (player.name, territory.name))

###############################################################################
## Attack phase DFA
#

def attack_phase(player, game_master):
    done = False
    while not done:
        event = scan_pygame_mouse_event()
        for name, clickable in get_clicked_territories(event.pos):
            if isinstance(clickable, TerritoryAsset):
                if clickable.territory.owner == player:
                    attack_choose_target(player, game_master, 
                            clickable.territory)
        for name, clickable in get_clicked_buttons(event.pos):
            if name == 'next':
                done = True

def attack_choose_target(player, game_master, origin):
    picasso = get_picasso()
    datastore = Datastore()
    feedback_asset = datastore.get_entry('attack_feedback')
    picasso.add_asset(LAYER, feedback_asset)
    target = wait_for_territory_click().territory
    try:
        success = game_master.player_attack(player, origin.name, target.name)
        if success:
            attack_success_move_armies(player, game_master, origin, target)
        else:
            attack_failed(player, game_master, origin, target)
    except (GameMasterError, RiskBattleError, KeyError):
        pass
    finally:
        picasso.remove_asset(LAYER, feedback_asset)

def attack_success_move_armies(player, game_master, origin, target):
    picasso = get_picasso()
    dialog = BlockingNumericDialogAsset(400, 300, 
            'Enter the number of armies to move')
    picasso.add_asset(LAYER, dialog)
    done = False
    while not done:
        number_to_move = dialog.get_user_key_input(INPUT_POLL_SLEEP, 1)
        try:
            game_master.player_move_armies(player, origin.name, target.name,
                    number_to_move)
            done = True
        except GameMasterError as e:
            print e
            dialog.reset()
        except ValueError:
            # we really shouldn't get a parsing error from numeric dialog
            raise 
    picasso.remove_asset(LAYER, dialog)

def attack_failed(player, game_master, origin, target):
    pass

###############################################################################
## Fortify phase DFA
#

def fortify_phase(player, game_master):
    done = False
    # TODO merge with attack phase block
    while not done:
        event = scan_pygame_mouse_event()
        for name, clickable in get_clicked_territories(event.pos):
            if isinstance(clickable, TerritoryAsset):
                if clickable.territory.owner == player:
                    fortify_choose_target(player, game_master, 
                            clickable.territory)
        for name, clickable in get_clicked_buttons(event.pos):
            if name == 'next':
                done = True

def fortify_choose_target(player, game_master, origin):
    picasso = get_picasso()
    dialog = BlockingNumericDialogAsset(400, 300, 
            'Enter the number of armies to move')
    try:
        target = wait_for_territory_click().territory
        picasso.add_asset(LAYER, dialog)
        armies_to_move = dialog.get_user_key_input(INPUT_POLL_SLEEP)
        game_master.player_move_armies(player, origin.name,
                target.name, armies_to_move)
        done = True
    except GameMasterError:
        pass
    picasso.remove_asset(LAYER, dialog)

