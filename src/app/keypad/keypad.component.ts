import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';

@Component({
  selector: 'app-keypad',
  templateUrl: './keypad.component.html',
  styleUrls: ['./keypad.component.css']
})

export class KeypadComponent implements OnInit {
  @Input() defVal: any;
  @Output() passEntry: EventEmitter<any> = new EventEmitter();
  value = "";
  public keyboard: any;
  constructor (public activeModal: NgbActiveModal,
  ) { }

  ngOnInit (): void {
    console.log("Default Val : ", this.defVal);
    this.value = "" + this.defVal;
  }

  keyPress (key: any) {
    switch (key) {
      case "Done":
        // console.log("Done Pressed", this.value);
        console.log("Submitting : ", this.value);
        this.passEntry.emit(this.value);
        break;
      case "Cancel":
        console.log("Restoring Default : ", this.defVal);
        this.passEntry.emit(this.defVal);
        break;
      case "Clear":
        if (this.value.length > 0) {
          this.value = '';
        }
        break;
      default:
        this.value = this.value + key;
        break;
    }
  }
}