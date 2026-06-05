import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';

@Component({
  selector: 'app-keyboard',
  templateUrl: './keyboard.component.html',
  styleUrls: ['./keyboard.component.css']
})
export class KeyboardComponent implements OnInit {
  @Input() defVal: any;
  @Output() passEntry: EventEmitter<any> = new EventEmitter();
  wifipassword:string="";
  constructor(public activeModal: NgbActiveModal) { }

  ngOnInit(): void {
  }
  submit(){
    this.passEntry.emit(this.wifipassword);
  }
  cancel(){
    this.passEntry.emit("------")
  }
}
