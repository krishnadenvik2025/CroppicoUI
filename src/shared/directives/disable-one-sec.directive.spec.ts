import { ElementRef } from '@angular/core';
import { DisableOneSecDirective } from './disable-one-sec.directive';

describe('DisableOneSecDirective', () => {
  it('should create an instance', () => {
    const directive = new DisableOneSecDirective(new ElementRef({}));
    expect(directive).toBeTruthy();
  });
});
