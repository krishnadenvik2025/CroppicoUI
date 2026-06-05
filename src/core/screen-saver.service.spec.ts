import { TestBed } from '@angular/core/testing';

import { ScreenSaverService } from './screen-saver.service';

describe('ScreenSaverService', () => {
  let service: ScreenSaverService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ScreenSaverService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
