import { Directive, HostListener, ElementRef } from '@angular/core';

@Directive({
  selector: '[disableOneSec]'
})
export class DisableOneSecDirective {

  constructor (private el: ElementRef) { }

  @HostListener('click', ['$event']) onClick (event: Event) {
    const button = this.el.nativeElement as HTMLButtonElement;
    this.disableButton(button);

    // Perform API call after re-enabling the button
    setTimeout(() => {
      // Replace this with your API call code
      console.log('API call triggered');
    }, 1000); // Adjust the time to match the re-enable time
  }

  disableButton (button: HTMLButtonElement) {
    button.disabled = true;

    setTimeout(() => {
      button.disabled = false;
      console.log('Button re-enabled');
    }, 1000); // Re-enable the button after one second
  }
}
