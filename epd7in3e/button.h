#ifndef BUTTON_H
#define BUTTON_H

#include "config.h"

class Button
{
private:
    const int pin;
    const unsigned long debounceDelay = BUTTON_DEBOUNCE;  // 使用config.h的防抖延遲
    const unsigned long longPressTime = BUTTON_HOLD_TIME; // 使用config.h的長按時間
    bool lastButtonState = HIGH;
    unsigned long lastDebounceTime = 0;
    unsigned long pressStartTime = 0;
    bool isPressed = false;
    bool longPressDetected = false;
    bool hasEvent = false;

public:
    Button(int buttonPin) : pin(buttonPin) {}

    bool result()
    {
        unsigned long startCheckTime = millis();
        unsigned long noEventTime = millis();

        while (millis() - startCheckTime < (longPressTime + 500))
        {
            bool buttonState = digitalRead(pin);

            if (buttonState != lastButtonState)
            {
                lastDebounceTime = millis();
                hasEvent = true;
                noEventTime = millis();
                if (buttonState == LOW)
                {
                    pressStartTime = millis();
                    isPressed = true;
                    longPressDetected = false;
                }
            }

            if (!hasEvent && (millis() - noEventTime >= 1500))
            {
                return false;
            }

            if (isPressed && !longPressDetected)
            {
                if ((millis() - pressStartTime) >= longPressTime)
                {
                    longPressDetected = true;
                    Serial.println(F("long press"));
                    return true;
                }
            }

            lastButtonState = buttonState;
            // Serial.println(F("normal click"));
            delay(10);
        }
        return false;
    }
};

#endif