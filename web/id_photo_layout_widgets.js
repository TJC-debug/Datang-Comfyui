// Keep the native widget instance: DOM widgets store names and values on
// prototype accessors and are also registered separately by ComfyUI.
export function hideDataWidget(node, originalWidget, onExternalValue) {
    if (!node.widgets?.includes(originalWidget)) return null;
    let internalWrite = false;
    let callbackCalled = false;
    const originalCallback = originalWidget.callback;

    originalWidget.callback = function (...args) {
        callbackCalled = true;
        const result = originalCallback?.apply(this, args);
        if (!internalWrite) onExternalValue?.(this.value);
        return result;
    };
    originalWidget.writeFromUi = function (value) {
        internalWrite = true;
        callbackCalled = false;
        try {
            this.value = value;
            // DOM setters call the callback; plain number widgets do not.
            if (!callbackCalled) this.callback?.(this.value);
        } finally {
            internalWrite = false;
        }
    };
    originalWidget.hidden = true;
    originalWidget.datangHidden = true;
    originalWidget.computeSize = () => [0, -4];
    originalWidget.computeLayoutSize = () => ({ minHeight: 0, maxHeight: 0, minWidth: 0 });
    originalWidget.draw = () => {};
    originalWidget.serializeValue = function () { return this.value; };
    const element = originalWidget.inputEl || originalWidget.element;
    if (element?.style) element.style.display = "none";
    return originalWidget;
}

// Native plain widgets may not call their callbacks during graph loading.
// Reconcile the visible panel only after all saved widget values are restored.
export function afterLayoutConfigured(node, reconcile) {
    const originalConfigure = node.onConfigure;
    node.onConfigure = function (...args) {
        const result = originalConfigure?.apply(this, args);
        reconcile();
        return result;
    };
}
