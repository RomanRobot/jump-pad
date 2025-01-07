import Quartz
import sys

class Constants:
    kVK_Space = 0x31
    kVK_Shift = 0x38
    kCustomEventFlagMaskSynthesized = 1 << 21 # kCGEventFlagMaskCommand is the highest predefined flag with a value of 1 << 20

is_shift_synthesized = False
is_left_mouse_synthesized = False
is_right_mouse_synthesized = False
previous_flags = 0

def post_keyboard_event(key_code, down, original_event):
    synthesized_event = Quartz.CGEventCreateKeyboardEvent(None, key_code, down)
    flags = Quartz.CGEventGetFlags(original_event) | Constants.kCustomEventFlagMaskSynthesized
    if is_shift_synthesized:
        flags |= Quartz.kCGEventFlagMaskShift
    Quartz.CGEventSetFlags(synthesized_event, flags)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, synthesized_event)

def post_mouse_event(mouse_button, mouse_event, original_event):
    synthesized_event = Quartz.CGEventCreateMouseEvent(
        None,
        mouse_event,
        Quartz.CGEventGetLocation(original_event),
        mouse_button
    )
    flags = Quartz.CGEventGetFlags(original_event) | Constants.kCustomEventFlagMaskSynthesized
    if is_shift_synthesized:
        flags |= Constants.kCGEventFlagMaskShift
    Quartz.CGEventSetFlags(synthesized_event, flags)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, synthesized_event)

def callback(proxy, event_type, event, refcon):
    global is_shift_synthesized
    global is_left_mouse_synthesized
    global is_right_mouse_synthesized
    global previous_flags
    if Quartz.CGEventGetFlags(event) & Constants.kCustomEventFlagMaskSynthesized:
        return event
    
    # TODO: Investigate what event_type 29 is. Seems like some type of mouse move.
    #if event_type != Quartz.kCGEventMouseMoved and event_type != Quartz.kCGEventLeftMouseDragged and event_type != Quartz.kCGEventRightMouseDragged:
    #    print(f"Natural event received: {event_type}")

    match event_type:
        case Quartz.kCGEventLeftMouseDown:
            post_keyboard_event(Constants.kVK_Space, True, event)
            return None
        case Quartz.kCGEventLeftMouseUp:
            post_keyboard_event(Constants.kVK_Space, False, event)
            return None
        case Quartz.kCGEventRightMouseDown:
            is_shift_synthesized = True
            post_keyboard_event(Constants.kVK_Shift, True, event)
            # TODO: Quartz.kCGEventFlagsChanged instead of Quartz.kCGEventKeyDown
            return None
        case Quartz.kCGEventRightMouseUp:
            is_shift_synthesized = False
            post_keyboard_event(Constants.kVK_Shift, False, event)
            # TODO: Quartz.kCGEventFlagsChanged instead of Quartz.kCGEventKeyDown
            return None
        case Quartz.kCGEventKeyDown:
            key_code = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
            if key_code == Constants.kVK_Space:
                if is_left_mouse_synthesized:
                    # Ignore repeated keys
                    return None
                is_left_mouse_synthesized = True
                post_mouse_event(Quartz.kCGMouseButtonLeft, Quartz.kCGEventLeftMouseDown, event)
                return None
        case Quartz.kCGEventKeyUp:
            key_code = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
            if key_code == Constants.kVK_Space:
                is_left_mouse_synthesized = False
                post_mouse_event(Quartz.kCGMouseButtonLeft, Quartz.kCGEventLeftMouseUp, event)
                return None
        case Quartz.kCGEventFlagsChanged:
            current_flags = Quartz.CGEventGetFlags(event)
            changed_flags = current_flags ^ previous_flags
            previous_flags = current_flags
            if changed_flags & Quartz.kCGEventFlagMaskShift:
                if current_flags & Quartz.kCGEventFlagMaskShift:
                    is_right_mouse_synthesized = True
                    post_mouse_event(Quartz.kCGMouseButtonRight, Quartz.kCGEventRightMouseDown, event)
                else:
                    is_right_mouse_synthesized = False
                    post_mouse_event(Quartz.kCGMouseButtonRight, Quartz.kCGEventRightMouseUp, event)
                return None
        case Quartz.kCGEventMouseMoved:
            if is_left_mouse_synthesized:
                Quartz.CGEventSetType(event, Quartz.kCGEventLeftMouseDragged)
            if is_right_mouse_synthesized:
                Quartz.CGEventSetType(event, Quartz.kCGEventRightMouseDragged)
            # TODO: Might want to handle both mouse buttons simultaneously. Handle all 4 permutations.

    flags = Quartz.CGEventGetFlags(event)
    if is_shift_synthesized:
        flags |= Quartz.kCGEventFlagMaskShift
    else:
        flags &= ~Quartz.kCGEventFlagMaskShift
    Quartz.CGEventSetFlags(event, flags)

    return event

def main():
    tap = Quartz.CGEventTapCreate(
        Quartz.kCGHIDEventTap,
        Quartz.kCGHeadInsertEventTap,
        Quartz.kCGEventTapOptionDefault,
        Quartz.kCGEventMaskForAllEvents,
        callback,
        None
    )
    if not tap:
        print("Failed to create event tap.")
        sys.exit(1)

    run_loop_source = Quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
    run_loop = Quartz.CFRunLoopGetCurrent()
    Quartz.CFRunLoopAddSource(run_loop, run_loop_source, Quartz.kCFRunLoopCommonModes)
    Quartz.CGEventTapEnable(tap, True)
    Quartz.CFRunLoopRun()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
